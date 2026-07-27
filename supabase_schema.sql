-- Create users table (simple, just in case)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create listings table
CREATE TABLE IF NOT EXISTS listings (
    url TEXT PRIMARY KEY,
    modelo TEXT,
    estado TEXT,
    precio NUMERIC,
    precio_mercado TEXT,
    ahorro_porcentaje TEXT,
    plataforma TEXT,
    imagen TEXT,
    reverb TEXT,
    mensaje_borrador TEXT,
    last_seen DOUBLE PRECISION,
    fecha_agregado TEXT
);
