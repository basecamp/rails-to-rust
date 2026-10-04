# Run through the configured Rails runner, never a guessed local Ruby.
# Uses APIs from Rails 2.3 as well as Journey-era Rails. Output is evidence, not a router.
require "json"
require "digest"

module RailsToRust
  def self.encode(value)
    case value
    when String
      # Rails SafeBuffer subclasses can override to_json; old JSON gems call it even
      # inside pretty_generate, corrupting non-BMP text. Export plain String bytes.
      String.new(value)
    when NilClass, TrueClass, FalseClass, Numeric then value
    when Symbol then value.to_s
    when Regexp then { "regexp" => value.source, "options" => value.options }
    when Array then value.map { |item| encode(item) }
    when Hash
      result = {}
      value.each { |key, item| result[key.to_s] = encode(item) }
      result
    else
      # Do not pretend arbitrary Rack endpoints or callable constraints are plain strings.
      { "ruby_class" => value.class.name, "requires_review" => true }
    end
  end

  def self.routes
    if defined?(Rails) && Rails.respond_to?(:application) && Rails.application
      Rails.application.routes.routes.each_with_index.map do |route, ordinal|
        {
          "ordinal" => ordinal,
          "name" => route.respond_to?(:name) ? route.name : nil,
          "path" => route.path.spec.to_s,
          "verb" => encode(route.verb),
          "defaults" => encode(route.defaults),
          "requirements" => route.respond_to?(:requirements) ? encode(route.requirements) : {},
          "constraints" => route.respond_to?(:constraints) ? encode(route.constraints) : {},
          "endpoint_class" => route.app.class.name,
          "internal" => route.respond_to?(:internal) ? route.internal : false
        }
      end
    elsif defined?(ActionController::Routing::Routes)
      router = ActionController::Routing::Routes
      named = {}
      router.named_routes.routes.each { |name, route| named[route.object_id] = name.to_s }
      router.routes.each_with_index.map do |route, ordinal|
        {
          "ordinal" => ordinal, "name" => named[route.object_id],
          "path" => route.segments.map { |segment| segment.to_s }.join,
          "verb" => encode(route.conditions[:method]),
          "pattern" => route.send(:recognition_pattern),
          "defaults" => encode(route.defaults), "requirements" => encode(route.requirements),
          "constraints" => encode(route.conditions),
          "segments" => route.segments.map do |segment|
            result = { "class" => segment.class.name, "text" => segment.to_s, "optional" => segment.optional? }
            result["key"] = segment.key.to_s if segment.respond_to?(:key)
            result["regexp"] = encode(segment.regexp) if segment.respond_to?(:regexp)
            result["default"] = encode(segment.default) if segment.respond_to?(:default)
            result
          end
        }
      end
    else
      raise "unsupported Rails route registry: inspect this runtime and add an exporter"
    end
  end

  def self.schema
    connection = ActiveRecord::Base.connection
    connection.tables.sort.map do |table|
      {
        "name" => table, "primary_key" => encode(connection.primary_key(table)),
        "columns" => connection.columns(table).map do |column|
          {
            "name" => column.name, "type" => column.type.to_s,
            "sql_type" => column.sql_type, "null" => column.null,
            "default" => encode(column.default),
            "limit" => column.limit,
            "precision" => column.respond_to?(:precision) ? column.precision : nil,
            "scale" => column.respond_to?(:scale) ? column.scale : nil,
            "unsigned" => !!(column.sql_type =~ /\bunsigned\b/i),
            "array" => column.respond_to?(:array) ? column.array : false
          }
        end,
        "indexes" => connection.indexes(table).map do |index|
          { "name" => index.name, "columns" => encode(index.columns), "unique" => index.unique }
        end
      }
    end
  end

  def self.runtime
    rails_version = defined?(Rails::VERSION::STRING) ? Rails::VERSION::STRING : "unknown"
    connection = ActiveRecord::Base.connection
    adapter = connection.respond_to?(:adapter_name) ? connection.adapter_name : connection.class.name
    gems = {}
    Gem.loaded_specs.keys.sort.each do |name|
      spec = Gem.loaded_specs[name]
      # Keep the installed basename (including Git revision suffixes), not the
      # developer's absolute bundle path, in portable committed evidence.
      gems[name] = { "version" => spec.version.to_s, "source" => File.basename(String.new(spec.full_gem_path)) }
    end
    { "ruby_version" => RUBY_VERSION, "ruby_patchlevel" => RUBY_PATCHLEVEL, "rails_version" => rails_version,
      "adapter" => adapter, "gems" => gems }
  end
end

kind = ENV.fetch("RAILS_TO_RUST_EXPORT")
data = case kind
       when "routes" then RailsToRust.routes
       when "schema" then RailsToRust.schema
       when "runtime" then RailsToRust.runtime
       else raise "unknown export #{kind}"
       end
puts "--- RAILS_TO_RUST_JSON_BEGIN ---"
puts JSON.pretty_generate(RailsToRust.encode({
  "version" => 1, "kind" => kind, "reference_sha" => ENV.fetch("RAILS_TO_RUST_REFERENCE_SHA"),
  "runtime" => RailsToRust.runtime, "data" => data
}))
puts "--- RAILS_TO_RUST_JSON_END ---"
