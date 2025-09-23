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
        
        # Basic Python for virtual environment setup
        python = pkgs.python311;

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
            
            # Python for virtual environment setup
            python
            python.pkgs.pip
            python.pkgs.virtualenv
            
            # Modern Python development tools
            ruff  # All-in-one linter and formatter
            
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
            pre-commit
            
            # System dependencies for Python packages
            gcc
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
            echo "  - Python $(python --version)"
            echo "  - Node.js $(node --version)"
            echo "  - Podman $(podman --version | head -n1)"
            echo "  - PostgreSQL $(postgres --version | cut -d' ' -f3)"
            echo ""
            echo "Quick start:"
            echo "  1. Copy .env.example to .env and configure"
            echo "  2. Setup Python: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev,test]'"
            echo "  3. Setup Frontend: cd frontend && npm install"
            echo "  4. Start infrastructure: podman-compose up -d"
            echo "  5. Start backend: cd backend && source .venv/bin/activate && python -m app.main"
            echo "  6. Start frontend: cd frontend && npm run dev"
            echo ""
            
            # Set up environment
            export PYTHONPATH="$PWD/backend:$PYTHONPATH"
            export NODE_ENV=development
            export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
            export BUILDAH_FORMAT=docker
            
            # Create necessary directories
            mkdir -p data/{raw,processed}
            mkdir -p logs
            
            # Note: spaCy model will be downloaded when setting up the virtual environment
            
            # Check if .env exists
            if [ ! -f .env ]; then
              echo "⚠️  .env file not found. Copy .env.example to .env and configure."
            fi
            
            # Start podman socket if not running
            if ! systemctl --user is-active --quiet podman.socket; then
              echo "🔧 Starting podman socket..."
              systemctl --user start podman.socket 2>/dev/null || echo "Note: Run 'systemctl --user enable --now podman.socket' to enable podman socket"
            fi
            
            # Development aliases - add them as functions
            dc() { podman-compose "$@"; }
            dcu() { podman-compose up -d "$@"; }
            dcd() { podman-compose down "$@"; }
            dcl() { podman-compose logs -f "$@"; }
            dcr() { podman-compose restart "$@"; }
            
            be-dev() { cd backend && source .venv/bin/activate && python -m app.main; }
            be-test() { cd backend && source .venv/bin/activate && python -m pytest "$@"; }
            be-lint() { cd backend && ruff check --fix . && ruff format . && echo "✅ Code quality checks passed!"; }
            
            fe-dev() { cd frontend && npm run dev; }
            fe-build() { cd frontend && npm run build; }
            fe-test() { cd frontend && npm test "$@"; }
            fe-lint() { cd frontend && npm run lint; }
            
            psql-local() { psql postgresql://veracity_user:veracity_password@localhost:5432/veracity "$@"; }
            mongo-local() { mongosh mongodb://veracity_user:veracity_password@localhost:27017/veracity "$@"; }
            redis-cli-local() { redis-cli -h localhost -p 6379 "$@"; }
            
            logs-backend() { podman logs -f veracity-backend "$@"; }
            logs-frontend() { podman logs -f veracity-frontend "$@"; }
            logs-ingestion() { podman logs -f veracity-ingestion-worker "$@"; }
            
            start-dev() { podman-compose up -d postgres mongodb redis elasticsearch; }
            stop-dev() { podman-compose down; }
            reset-dev() { podman-compose down -v && podman-compose up -d; }
          '';
        };

        # Additional flake outputs
        packages = {
          # Build backend container
          backend-image = pkgs.dockerTools.buildLayeredImage {
            name = "veracity-backend";
            tag = "latest";
            
            contents = with pkgs; [
              python
              bash
              coreutils
              curl
            ];
            
            config = {
              Cmd = [ "${python}/bin/python" "-m" "app.main" ];
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
            buildInputs = [ python pkgs.ruff ];
          } ''
            cd ${self}/backend
            ${pkgs.ruff}/bin/ruff check .
            ${pkgs.ruff}/bin/ruff format --check .
            touch $out
          '';
          
          backend-test = pkgs.runCommand "backend-test" {
            buildInputs = [ python ];
          } ''
            cd ${self}/backend
            ${python}/bin/python -m venv .venv
            source .venv/bin/activate
            pip install -e '.[dev,test]'
            python -m pytest tests/
            touch $out
          '';
        };
      }
    );
}