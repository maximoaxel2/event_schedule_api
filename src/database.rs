use sqlx::{PgPool, postgres};	
use std::sync::OnceLock;

static DB_POOL: OnceLock<PgPool> = OnceLock::new();

pub async fn init_db_pool() {
    let db_conn_str: String = std::env::var("DATABASE_URL").expect("missing DATABASE_URL");
    let pool: PgPool = postgres::PgPool::connect(&db_conn_str)
        .await
        .expect("Couldn't connect to database");
    
    DB_POOL.set(pool).expect("Database pool was already initialized");
}

pub fn get_pool() -> &'static PgPool {
    DB_POOL.get().expect("Database pool was not initialized! Call init_db_pool() first.")
}