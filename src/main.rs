use tokio;
use anyhow::Result;

mod types;
mod endpoints;
mod database;
mod server;

#[tokio::main]
async fn main() -> Result<()> {
    dotenv::dotenv().ok();
    database::init_db_pool().await;
    server::start().await?;
    Ok(())
}
