# Documentation to start project

1. `git clone https://github.com/vaImantas/VA-InvenTree.git`

2. `cd VA-InvenTree`

3. `docker compose run inventree-dev-server invoke install`

4. `docker compose run inventree-dev-server invoke setup-test --dev`

5. run server:`docker compose up -d`
- your server now running at http://localhost:8000


6. `docker compose run inventree-dev-server invoke update --no-frontend`

7. pakeisti superuser prisijungimus (pakeitimas tik pas save kompe, lokaliai)

- `docker compose run inventree-dev-server invoke superuser`