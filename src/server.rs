use axum::{Router, routing::get};
use anyhow::Result;

use crate::endpoints;

pub async fn start() -> Result<()> {
   let app_port = std::env::var("APP_PORT")?;

   let app = Router::new()
      .route("/api/sessions", get(endpoints::get_sessions));

   let listener = tokio::net::TcpListener::bind("0.0.0.0:".to_owned() + &app_port).await.unwrap();
   axum::serve(listener, app).await?;

   Ok(())
}