CREATE TABLE IF NOT EXISTS ecommerce_events (
    event_id UUID PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('view', 'purchase')),
    price NUMERIC(10,2),
    event_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_time
ON ecommerce_events(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_event_type
ON ecommerce_events(event_type);

CREATE INDEX IF NOT EXISTS idx_user_id
ON ecommerce_events(user_id);