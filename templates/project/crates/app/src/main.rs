use axum::{Router, http::StatusCode};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let port = std::env::var("PORT").unwrap_or_else(|_| "7070".into()).parse::<u16>()?;
    let listener = tokio::net::TcpListener::bind(("127.0.0.1", port)).await?;
    // The scaffold must visibly fail parity until actual controllers replace it.
    let app = Router::new().fallback(|| async { (StatusCode::NOT_IMPLEMENTED, "Application behavior has not been ported") });
    axum::serve(listener, app)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}
