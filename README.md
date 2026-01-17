# MarketPulse: Real-Time Stock Data Pipeline with Snowflake, dbt & Airflow



## Overview

MarketPulse is a comprehensive real-time stock data pipeline that integrates modern data engineering technologies to deliver low-latency financial insights. The system leverages **Kafka** for streaming ingestion, **Snowflake** for cloud data warehousing, **dbt** for transformation workflows, **Airflow** for orchestration, and **Streamlit** for visualization. This architecture reduces decision latency by unifying traditionally siloed processes of data ingestion, transformation, and analytics into a single cohesive pipeline.

The project delivers an **open-source**, **reproducible implementation** that serves as both a practical trading analytics tool and an educational reference architecture for streaming data systems in financial contexts.

## Key Features

- **Real-time Data Ingestion**: Minute-level stock price ticks from Finnhub.io API
- **Streaming Architecture**: Kafka producer/consumer with MinIO for durable storage
- **Orchestration**: Airflow DAGs for end-to-end workflow management
- **Multi-layer Storage**: BRONZE–SILVER–GOLD data architecture in Snowflake
- **Transformation Layer**: dbt models with data quality tests and documentation
- **Interactive Dashboard**: Streamlit app with multiple analytical views:
  - OHLC candlestick charts with trend lines
  - Daily returns distribution
  - Cumulative performance tracking
  - Cross-asset normalized comparison
  - Rolling volatility analysis with interactive window control

## System Architecture

The pipeline consists of six interconnected components:

1. **Data Source**: Finnhub.io API (real-time stock ticks)
2. **Data Ingestion**: Kafka + MinIO (streaming + durable object storage)
3. **Orchestration**: Apache Airflow (task scheduling and coordination)
4. **Storage**: Snowflake (BRONZE/SILVER/GOLD layers)
5. **Transformation**: dbt (SQL-based modeling, testing, documentation)
6. **Visualization**: Streamlit (interactive financial dashboard)

## Prerequisites

Before you begin, ensure you have the following:

- Docker and Docker Compose
- Python 3.9+
- Snowflake account with admin privileges
- Finnhub API key (free tier: [finnhub.io](https://finnhub.io))
- AWS-compatible credentials for MinIO (local S3-compatible storage)

## Setup Instructions

### Local Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/MarketPulse-Real-Time-Stock-Pipeline/MarketPulse.git
   cd MarketPulse
   ```

2. Create and populate your environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your Snowflake, Finnhub, and MinIO credentials
   ```

3. Start all services:
   ```bash
   docker-compose up -d
   ```

4. Initialize Snowflake schema and stages:
   ```bash
   python scripts/init_snowflake.py
   ```

5. Run dbt transformations:
   ```bash
   cd dbt_project && dbt run
   ```

6. Access the dashboard at:
   ```
   http://localhost:8501
   ```

### Cloud Deployment (Optional)

1. Use Terraform templates in `/terraform` to provision infrastructure
2. Configure Airflow connections (Snowflake, MinIO, etc.)
3. Upload the `dbt_project` to cloud storage
4. Schedule the `minio_to_snowflake` DAG in Airflow
5. Deploy the Streamlit app to your preferred cloud platform (AWS/GCP/Azure)



## Dashboard Views

- **TSLA Price View**: OHLC candlesticks + smoothed close + trend line
- **Daily Returns**: Histogram showing distribution of daily % changes
- **Cumulative Returns**: Area chart tracking compounded performance
- **Cross-Stock Comparison**: Normalized price series for multiple tickers
- **Volatility Analysis**: Interactive rolling volatility with adjustable window




## Documentation

Full documentation includes:
- Architecture diagrams
- Setup guides
- API references
- Dashboard user manual
- Performance tuning tips

See the `/docs` folder for details.

## License

MIT License — see [LICENSE](LICENSE) for full terms.

---

