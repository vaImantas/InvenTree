# Documentation

git clone https://github.com/vaImantas/InvenTree.git
cd InvenTree
docker compose run inventree-dev-server invoke install
docker compose run inventree-dev-server invoke setup-test --dev
docker compose up -d
your server now running at http://localhost:8000

docker compose run inventree-dev-server invoke update --no-frontend

pakeisti superuser prisijungimus
docker compose run inventree-dev-server invoke superuser