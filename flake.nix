{
  description = "Veracity - Social Media Trend & News Trustability Platform";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python environment with all required packages
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          # Web framework
          fastapi
          uvicorn
          
          # Database drivers
          psycopg2
          pymongo
          redis
          elasticsearch
          
          # HTTP clients
          httpx
          aiohttp
          requests
          
          # Social Media APIs
          tweepy
          praw
          
          # ML/NLP packages
          torch
          transformers
          scikit-learn
          pandas
          numpy
          sentence-transformers
          spacy
          
          # Message queue
          aiokafka
          
          # Async support
          asyncio-mqtt
          
          # Utilities
          python-dotenv
          structlog
          celery
          croniter
          pydantic
          pydantic-settings
          
          # Development tools
          pytest
          pytest-asyncio
          black
          isort
          flake8
          pre-commit
          
          # Additional dependencies
          sqlalchemy
          alembic
          motor
          networkx
          matplotlib
          seaborn
        ]);

        # Node.js environment
        nodeEnv = pkgs.nodejs_20;
        
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Core development tools
            git
            curl
            wget
            jq
            tree
            
            # Container tools (Podman ecosystem)
            podman
            podman-compose
            buildah
            skopeo
            crun
            
            # Python environment
            pythonEnv
            
            # Node.js and package managers
            nodeEnv
            yarn
            pnpm
            
            # Database tools
            postgresql_15
            mongodb-tools
            redis
            
            # Development utilities
            tmux
            vim
            neovim
            
            # System dependencies for Python packages
            gcc
            g++
            pkg-config
            openssl
            libffi
            zlib
            
            # spaCy language models (we'll download these in the shell hook)
            
            # Container networking
            nettools
            iproute2
            
            # Monitoring tools
            htop
            bottom
            
            # Text processing
            ripgrep
            fd
            bat
            
            # Docker Compose compatibility
            docker-compose
          ];

          shellHook = ''
            echo "🚀 Veracity Development Environment"
            echo "=================================="
            echo ""
            echo "Available tools:"
            echo "  - Python ${pythonEnv.python.version} with ML/NLP packages"
            echo "  - Node.js $(node --version)"
            echo "  - Podman $(podman --version | head -n1)"
            echo "  - PostgreSQL $(postgres --version | cut -d' ' -f3)"
            echo ""
            echo "Quick start:"
            echo "  1. Copy .env.example to .env and configure"
            echo "  2. Run: podman-compose up -d"
            echo "  3. Start backend: cd backend && python -m app.main"
            echo "  4. Start frontend: cd frontend && npm run dev"
            echo ""
            
            # Set up environment
            export PYTHONPATH="$PWD/backend:$PYTHONPATH"
            export NODE_ENV=development
            
            # Podman configuration for rootless mode
            export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
            
            # Create necessary directories
            mkdir -p data/{raw,processed}
            mkdir -p logs
            
            # Download spaCy model if not present
            if ! python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
              echo "📥 Downloading spaCy English model..."
              python -m spacy download en_core_web_sm
            fi
            
            # Check if .env exists
            if [ ! -f .env ]; then
              echo "⚠️  .env file not found. Copy .env.example to .env and configure."
            fi
            
            # Start podman socket if not running
            if ! systemctl --user is-active --quiet podman.socket; then
              echo "🔧 Starting podman socket..."
              systemctl --user start podman.socket 2>/dev/null || echo "Note: Run 'systemctl --user enable --now podman.socket' to enable podman socket"
            fi
          '';

          # Environment variables
          PYTHONPATH = "./backend";
          DOCKER_HOST = "unix:///run/user/1000/podman/podman.sock";
          BUILDAH_FORMAT = "docker";
          
          # Development aliases
          shellAliases = {
            # Container management
            dc = "podman-compose";
            dcu = "podman-compose up -d";
            dcd = "podman-compose down";
            dcl = "podman-compose logs -f";
            dcr = "podman-compose restart";
            
            # Backend shortcuts
            be-dev = "cd backend && python -m app.main";
            be-test = "cd backend && python -m pytest";
            be-lint = "cd backend && black . && isort . && flake8 .";
            
            # Frontend shortcuts
            fe-dev = "cd frontend && npm run dev";
            fe-build = "cd frontend && npm run build";
            fe-test = "cd frontend && npm test";
            fe-lint = "cd frontend && npm run lint";
            
            # Database shortcuts
            psql-local = "psql postgresql://veracity_user:veracity_password@localhost:5432/veracity";
            mongo-local = "mongosh mongodb://veracity_user:veracity_password@localhost:27017/veracity";
            redis-cli-local = "redis-cli -h localhost -p 6379";
            
            # Utility shortcuts
            logs-backend = "podman logs -f veracity-backend";
            logs-frontend = "podman logs -f veracity-frontend";
            logs-ingestion = "podman logs -f veracity-ingestion-worker";
            
            # Development workflow
            start-dev = "podman-compose up -d postgres mongodb redis elasticsearch";
            stop-dev = "podman-compose down";
            reset-dev = "podman-compose down -v && podman-compose up -d";
          };
        };

        # Additional flake outputs
        packages = {
          # Build backend container
          backend-image = pkgs.dockerTools.buildLayeredImage {
            name = "veracity-backend";
            tag = "latest";
            
            contents = with pkgs; [
              pythonEnv
              bash
              coreutils
              curl
            ];
            
            config = {
              Cmd = [ "${pythonEnv}/bin/python" "-m" "app.main" ];
              WorkingDir = "/app";
              ExposedPorts = {
                "8000/tcp" = {};
              };
            };
          };
          
          # Build frontend container  
          frontend-image = pkgs.dockerTools.buildLayeredImage {
            name = "veracity-frontend";
            tag = "latest";
            
            contents = with pkgs; [
              nodeEnv
              bash
              coreutils
            ];
            
            config = {
              Cmd = [ "${nodeEnv}/bin/npm" "run" "start" ];
              WorkingDir = "/app";
              ExposedPorts = {
                "3000/tcp" = {};
              };
            };
          };
        };

        # Development checks
        checks = {
          backend-lint = pkgs.runCommand "backend-lint" {
            buildInputs = [ pythonEnv ];
          } ''
            cd ${self}
            python -m black --check backend/
            python -m isort --check-only backend/
            python -m flake8 backend/
            touch $out
          '';
          
          backend-test = pkgs.runCommand "backend-test" {
            buildInputs = [ pythonEnv ];
          } ''
            cd ${self}
            python -m pytest backend/tests/
            touch $out
          '';
        };
      }
    );
}