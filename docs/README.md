# Documentation

git clone https://github.com/vaImantas/VA-InvenTree.git
<br>
cd VA-InvenTree
<br>
docker compose run inventree-dev-server invoke install
<br>
docker compose run inventree-dev-server invoke setup-test --dev
<br>
docker compose up -d
<br>
your server now running at http://localhost:8000
<br>
<br>

docker compose run inventree-dev-server invoke update --no-frontend
<br>
pakeisti superuser prisijungimus (pakeitimas tik pas save kompe, lokaliai)
<br>
docker compose run inventree-dev-server invoke superuser
