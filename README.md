# Rental platform

Deux micro-services pour la location de voitures :

| Service | Langage | Port | Rôle |
|---|---|---|---|
| `apps/car-rental-service` | Java 21 / Spring Boot / Gradle | 8080 | Catalogue de voitures et devis de location (appelle le service de tarification) |
| `apps/pricing-service` | Python 3.12 / FastAPI | 8000 | Calcule le prix selon la catégorie et la durée |

```text
client ──> car-rental-service ──HTTP──> pricing-service
           /health /cars /cars/{id}/quote?days=N      /health /cars /quote?category=&days=
```

Règle métier de référence : une voiture `standard` louée 2 jours coûte **120 EUR**.

## Commandes locales

```bash
python scripts/course.py prerequisites
python scripts/course.py test          # tests Java puis Python
python scripts/course.py lint          # Checkstyle puis Ruff (lint-java / lint-python)
python scripts/course.py verify        # tests puis qualité, s'arrête au premier échec (code 1)
python scripts/course.py compose-up    # construit et démarre les services
python scripts/course.py smoke         # vérifie /health, /cars et le devis à 120 EUR
python scripts/course.py compose-down
```

Si les ports 8080 ou 8000 sont déjà occupés, définissez `CAR_RENTAL_PORT` et/ou
`PRICING_PORT` (par exemple `CAR_RENTAL_PORT=18080`) pour `compose-up` comme pour `smoke`.

Les dépendances Python s'installent avec :

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r apps/pricing-service/requirements-dev.txt   # Windows
# .venv/bin/python -m pip install -r apps/pricing-service/requirements-dev.txt     # Linux / macOS
```

## Intégration continue

| Workflow | Jobs (contrôles requis) |
|---|---|
| `Java service` | `Java tests`, `Java quality` → `Java Docker image` |
| `Python service` | `Python tests`, `Python quality` → `Python Docker image` |
| `Secret detection` | `Secret detection` (Gitleaks sur tout l'historique) |

`verify` reproduit localement les portes **tests et qualité** uniquement :
la construction des images, Gitleaks, la publication des rapports et la
protection de branche restent assurées par GitHub Actions.
