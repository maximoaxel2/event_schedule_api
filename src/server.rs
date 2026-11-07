use axum::{Router, routing::get};
use anyhow::Result;
use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

use crate::endpoints;
use crate::types::*;

#[derive(OpenApi)]
#[openapi(
    paths(
        endpoints::get_sessions
    ),
    components(
        schemas(
            Session, Event, Person, Entity, Location, Room, EventMode, EventType
        )
    )
)]
pub struct ApiDoc;

pub async fn start() -> Result<()> {
    let app_port = std::env::var("APP_PORT")?;

    let app = Router::new()
        .merge(SwaggerUi::new("/swagger-ui").url("/api-docs/openapi.json", ApiDoc::openapi()))
        .route("/api/sessions", get(endpoints::get_sessions));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:".to_owned() + &app_port).await.unwrap();
    
    println!("Server running on port {}", app_port);
    println!("Swagger UI available at http://localhost:{}/swagger-ui", app_port);
    
    axum::serve(listener, app).await?;

    Ok(())
}