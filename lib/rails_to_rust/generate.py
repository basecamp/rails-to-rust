from __future__ import annotations

import json
import os
from pathlib import Path
import re

from .common import Error, generated_path, write
from .oracle import vector

KEYWORDS = set("as break const continue crate else enum extern false fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait true type unsafe use where while async await dyn abstract become box do final macro override priv typeof unsized virtual yield try gen".split())


def literal(value):
    # Rust strings use \u{...}, whereas JSON's \uXXXX is not a Rust escape.
    result = '"'
    for char in value:
        result += {'"': '\\"', '\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t'}.get(
            char, f"\\u{{{ord(char):x}}}" if ord(char) < 32 else char)
    return result + '"'


def ident(value, *, field=False):
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value):
        raise Error(f"{value!r} cannot be mapped to a Rust identifier; add an explicit name mapping")
    if value in {"self", "Self", "super", "crate", "_"}:
        raise Error(f"{value!r} needs an explicit Rust field mapping")
    return "r#" + value if field and value in KEYWORDS else value


def records(root, source="vectors/schema.json", output="crates/db/src/generated.rs", *, force=False, tables=None):
    root, envelope = vector(root, source, "schema")
    out = [f"//! Generated from {source}, reference {envelope['reference_sha']}.",
           "//! Storage-shaped records only: implement reference typecasting in the DB adapter.",
           "//! No schema migration or callback behavior is generated.", "",
           "/// Preserve raw database timestamp/date/decimal text until an oracle-tested codec handles it.",
           "#[derive(Debug, Clone, PartialEq)]", "pub struct Timestamp(pub String);",
           "#[derive(Debug, Clone, PartialEq)]", "pub struct Date(pub String);",
           "#[derive(Debug, Clone, PartialEq)]", "pub struct Decimal(pub String);",
           "#[derive(Debug, Clone, PartialEq)]", "pub struct Json(pub String);", ""]
    types = {"string": "String", "text": "String", "boolean": "bool", "binary": "Vec<u8>",
             "datetime": "Timestamp", "timestamp": "Timestamp", "date": "Date", "time": "Timestamp",
             "decimal": "Decimal", "float": "f64", "json": "Json", "jsonb": "Json", "uuid": "String"}
    seen = set()
    selected = envelope["data"]
    if tables:
        missing = set(tables) - {table["name"] for table in selected}
        if missing:
            raise Error("unknown selected tables: " + ", ".join(sorted(missing)))
        selected = [table for table in selected if table["name"] in tables]
    for table in selected:
        name = table["name"]
        ident(name)
        # Avoid guessing Ruby inflections or confusing irregular model names with table names.
        record = "".join(part[:1].upper() + part[1:] for part in name.split("_")) + "Row"
        if record in seen:
            raise Error(f"Rust record-name collision: {record}")
        seen.add(record)
        columns = table.get("columns", [])
        if not columns or len({column["name"] for column in columns}) != len(columns):
            raise Error(f"{name}: empty or duplicate columns")
        out += [f"/// Storage fields from `{name}`; nullability and primary keys come from the live schema.",
                "#[derive(Debug, Clone, PartialEq)]", f"pub struct {record} {{"]
        for column in columns:
            if "null" not in column or not isinstance(column["null"], bool):
                raise Error(f"{name}.{column['name']}: explicit nullability is required")
            kind = column["type"]
            if column.get("array"):
                raise Error(f"{name}.{column['name']}: array columns need an explicit codec")
            if kind in {"integer", "bigint", "primary_key"}:
                ty = "u64" if column.get("unsigned", False) else "i64"
            else:
                try:
                    ty = types[kind]
                except KeyError as error:
                    raise Error(f"{name}.{column['name']}: unsupported type {kind}; implement its codec explicitly") from error
            if column["null"]:
                ty = f"Option<{ty}>"
            out += [f"    pub {ident(column['name'], field=True)}: {ty},"]
        primary = table.get("primary_key")
        primary = [] if primary is None else primary if isinstance(primary, list) else [primary]
        if not set(primary).issubset({column["name"] for column in columns}):
            raise Error(f"{name}: primary key is absent from columns")
        out += ["}", f"impl {record} {{", f"    pub const TABLE: &'static str = {literal(name)};",
                "    pub const COLUMNS: &'static [&'static str] = &[" + ", ".join(literal(c["name"]) for c in columns) + "];",
                "    pub const PRIMARY_KEY: &'static [&'static str] = &[" + ", ".join(literal(key) for key in primary) + "];", "}", ""]
    destination = generated_path(root, output)
    write(destination, "\n".join(out), force=force)
    return {"output": str(destination), "records": len(seen), "reference_sha": envelope["reference_sha"]}


def routes(root, source="vectors/routes.json", output="crates/routes/src/generated.rs", *, force=False):
    root, envelope = vector(root, source, "routes")
    out = [f"//! Ordered route contracts from {source}, reference {envelope['reference_sha']}.",
           "//! Implement recognition and URL generation against separate oracle vectors.",
           "//! The verb field may be a regexp or legacy method list; do not reorder by specificity.",
           "#[derive(Debug)]", "pub struct RouteContract {", "    pub ordinal: usize,",
           "    pub name: Option<&'static str>,", "    pub path: &'static str,",
           "    pub contract_json: &'static str,", "}", "", "pub static ROUTES: &[RouteContract] = &["]
    for ordinal, route in enumerate(envelope["data"]):
        if route.get("ordinal") != ordinal or not isinstance(route.get("path"), str):
            raise Error("route ordinals must describe the original recognition order, starting at zero")
        name = "None" if route.get("name") is None else f"Some({literal(route['name'])})"
        raw = literal(json.dumps(route, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
        out += [f"    RouteContract {{ ordinal: {ordinal}, name: {name}, path: {literal(route['path'])}, contract_json: {raw} }},"]
    out += ["];"]
    destination = generated_path(root, output)
    write(destination, "\n".join(out) + "\n", force=force)
    return {"output": str(destination), "routes": len(envelope["data"]), "reference_sha": envelope["reference_sha"]}


def contract_test(root, kind, source, output, *, force=False):
    root, envelope = vector(root, source, kind)
    name = ident(kind.replace("-", "_"))
    destination = generated_path(root, output)
    relative = Path(os.path.relpath(generated_path(root, source), destination.parent)).as_posix()
    out = f'''//! Reference-generated expectations. Add serde_json as a dev dependency to this crate.
//! Replace run_case with the real Rust implementation; unfinished cases must fail, not skip.

#[test]
fn {name}_matches_the_reference() {{
    let envelope: serde_json::Value = serde_json::from_str(include_str!({literal(relative)})).unwrap();
    let cases = envelope["data"].as_array().expect("oracle cases");
    assert!(!cases.is_empty());
    for case in cases {{
        let expected = case.get("expected").expect("oracle case needs expected");
        assert_eq!(&run_case(&case["input"]), expected, "{{case}}");
    }}
}}

fn run_case(_input: &serde_json::Value) -> serde_json::Value {{
    todo!("connect the oracle-backed {kind} implementation")
}}
'''
    for case in envelope["data"]:
        if not isinstance(case, dict) or "input" not in case or "expected" not in case:
            raise Error("contract-test data must contain input and expected for every case")
    write(destination, out, force=force)
    return {"output": str(destination), "cases": len(envelope["data"])}
