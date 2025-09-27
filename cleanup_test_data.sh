#!/usr/bin/env bash

# Test Data Cleanup Script for Veracity Platform
# This script cleans up test/mock data from PostgreSQL, MongoDB, and Redis

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧹 Starting test data cleanup for Veracity platform...${NC}"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓ Loaded environment variables from .env${NC}"
else
    echo -e "${RED}❌ .env file not found! Please ensure .env exists with database credentials.${NC}"
    exit 1
fi

# Extract database connection details from URLs or use individual vars
if [ -n "$POSTGRES_URL" ]; then
    # Extract from URL if available (format: postgresql+asyncpg://user:pass@host:port/db)
    POSTGRES_HOST=$(echo "$POSTGRES_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    POSTGRES_PORT=$(echo "$POSTGRES_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    POSTGRES_USER=$(echo "$POSTGRES_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    POSTGRES_PASSWORD=$(echo "$POSTGRES_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    POSTGRES_DB=$(echo "$POSTGRES_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
else
    # Use individual environment variables as fallback
    POSTGRES_HOST=${POSTGRES_HOST:-localhost}
    POSTGRES_PORT=${POSTGRES_PORT:-5432}
    POSTGRES_USER=${POSTGRES_USER:-veracity_user}
    POSTGRES_DB=${POSTGRES_DB:-veracity}
fi

if [ -n "$MONGODB_URL" ]; then
    # Extract from URL if available (format: mongodb://user:pass@host:port/db)
    MONGODB_HOST=$(echo "$MONGODB_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    MONGODB_PORT=$(echo "$MONGODB_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    MONGODB_USER=$(echo "$MONGODB_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    MONGODB_PASSWORD=$(echo "$MONGODB_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    MONGODB_DB=$(echo "$MONGODB_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')
else
    # Use individual environment variables as fallback
    MONGODB_HOST=${MONGODB_HOST:-localhost}
    MONGODB_PORT=${MONGODB_PORT:-27017}
    MONGODB_USER=${MONGODB_USER:-veracity_user}
    MONGODB_DB=${MONGODB_DB:-veracity}
fi

if [ -n "$REDIS_URL" ]; then
    # Extract from URL if available (format: redis://host:port/db)
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    REDIS_PORT=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
else
    # Use individual environment variables as fallback
    REDIS_HOST=${REDIS_HOST:-localhost}
    REDIS_PORT=${REDIS_PORT:-6379}
fi

echo -e "${YELLOW}📋 Database connection details:${NC}"
echo "  PostgreSQL: ${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "  MongoDB: ${MONGODB_USER}@${MONGODB_HOST}:${MONGODB_PORT}/${MONGODB_DB}"
echo "  Redis: ${REDIS_HOST}:${REDIS_PORT}"

# Function to check if service is running
check_service() {
    local service=$1
    local host=$2
    local port=$3
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✓ $service is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $service is not running on $host:$port${NC}"
        return 1
    fi
}

# Check if all services are running
echo -e "\n${YELLOW}🔍 Checking service availability...${NC}"
check_service "PostgreSQL" "$POSTGRES_HOST" "$POSTGRES_PORT" || exit 1
check_service "MongoDB" "$MONGODB_HOST" "$MONGODB_PORT" || exit 1
check_service "Redis" "$REDIS_HOST" "$REDIS_PORT" || exit 1

# PostgreSQL Cleanup
echo -e "\n${YELLOW}🐘 Cleaning up PostgreSQL data...${NC}"
export PGPASSWORD="$POSTGRES_PASSWORD"

# Get list of tables
TABLES=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';" | grep -v '^$' | tr -d ' ')

if [ -n "$TABLES" ]; then
    echo "  Found tables: $(echo $TABLES | tr '\n' ' ')"
    
    # Truncate all tables (faster than DELETE)
    for table in $TABLES; do
        echo "  Truncating table: $table"
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "TRUNCATE TABLE $table CASCADE;" > /dev/null
    done
    
    # Reset sequences
    echo "  Resetting sequences..."
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        DO \$\$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = 'public'
            LOOP
                EXECUTE 'ALTER SEQUENCE ' || quote_ident(r.schemaname) || '.' || quote_ident(r.sequencename) || ' RESTART WITH 1';
            END LOOP;
        END \$\$;
    " > /dev/null
    
    echo -e "${GREEN}✓ PostgreSQL cleanup complete${NC}"
else
    echo -e "${YELLOW}  No tables found in PostgreSQL${NC}"
fi

# MongoDB Cleanup
echo -e "\n${YELLOW}🍃 Cleaning up MongoDB data...${NC}"

# Get list of collections
COLLECTIONS=$(mongosh --host "$MONGODB_HOST:$MONGODB_PORT" -u "$MONGODB_USER" -p "$MONGODB_PASSWORD" --authenticationDatabase admin "$MONGODB_DB" --quiet --eval "db.getCollectionNames().join(' ')")

if [ -n "$COLLECTIONS" ] && [ "$COLLECTIONS" != "" ]; then
    echo "  Found collections: $COLLECTIONS"
    
    # Drop all collections
    for collection in $COLLECTIONS; do
        echo "  Dropping collection: $collection"
        mongosh --host "$MONGODB_HOST:$MONGODB_PORT" -u "$MONGODB_USER" -p "$MONGODB_PASSWORD" --authenticationDatabase admin "$MONGODB_DB" --quiet --eval "db.$collection.drop()" > /dev/null
    done
    
    echo -e "${GREEN}✓ MongoDB cleanup complete${NC}"
else
    echo -e "${YELLOW}  No collections found in MongoDB${NC}"
fi

# Redis Cleanup
echo -e "\n${YELLOW}🔴 Cleaning up Redis data...${NC}"

# Get database count
DB_COUNT=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" INFO keyspace | grep -c "^db" || echo "0")

if [ "$DB_COUNT" -gt 0 ]; then
    echo "  Found $DB_COUNT Redis databases with data"
    
    # Flush all Redis databases
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" FLUSHALL > /dev/null
    echo -e "${GREEN}✓ Redis cleanup complete${NC}"
else
    echo -e "${YELLOW}  No data found in Redis${NC}"
fi

# Verify cleanup
echo -e "\n${YELLOW}🔍 Verifying cleanup...${NC}"

# Check PostgreSQL
PG_ROWS=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "
    SELECT COALESCE(SUM(n_tup_ins + n_tup_upd), 0) 
    FROM pg_stat_user_tables;
" | tr -d ' ')
echo "  PostgreSQL total rows: $PG_ROWS"

# Check MongoDB
MONGO_DOCS=$(mongosh --host "$MONGODB_HOST:$MONGODB_PORT" -u "$MONGODB_USER" -p "$MONGODB_PASSWORD" --authenticationDatabase admin "$MONGODB_DB" --quiet --eval "
    let total = 0;
    db.getCollectionNames().forEach(name => {
        total += db.getCollection(name).countDocuments();
    });
    print(total);
" || echo "0")
echo "  MongoDB total documents: $MONGO_DOCS"

# Check Redis
REDIS_KEYS=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" DBSIZE)
echo "  Redis total keys: $REDIS_KEYS"

echo -e "\n${GREEN}🎉 Test data cleanup completed successfully!${NC}"
echo -e "${YELLOW}📊 Summary:${NC}"
echo "  - PostgreSQL: $PG_ROWS rows remaining"
echo "  - MongoDB: $MONGO_DOCS documents remaining" 
echo "  - Redis: $REDIS_KEYS keys remaining"

if [ "$PG_ROWS" -eq 0 ] && [ "$MONGO_DOCS" -eq 0 ] && [ "$REDIS_KEYS" -eq 0 ]; then
    echo -e "\n${GREEN}✅ All databases are clean and ready for testing!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Some data may still exist - this is normal for system tables/collections${NC}"
fi