Project 12 — Deploy in the Cloud, Read the Bill

Student: Mohammed Imad Uddin
Student ID: F00611260

PURPOSE
This repository illustrates an example of a cloud based application that is reproducible.
Predicts synthetic donor records for a calls a serverless model API, and uses only synthetic donor records.
stores token usage, reconciles the prediction and is cost before traffic.
Export cost to actual provider.

ARCHITECTURE

Application host:
Oracle Cloud Ubuntu 24.04 VM

Provider:
OpenAI Platform

Model:
gpt-5.4-mini-2026-03-17

Local service:
http://127.0.0.1:8012

Fixed paid workload:
200 requests

COST ALLOCATION

Provider project:
project12-grace-mercy-relief

Project-scoped API key name:
project12-env-lab-team-it-workload-donor-letters

Local allocation labels:
project=project12
env=lab
team=it
workload=donor-thank-you

INSTALLATION

1. Create a Python environment:

python3 -m venv "$HOME/project12-venv"

2. Activate it:

source "$HOME/project12-venv/bin/activate"

3. Install dependencies:

pip install -r requirements.txt

4. Create the private environment file:

cp .env.example .env

5. Edit .env and provide a project-scoped API key:

nano .env

6. Protect the file:

chmod 600 .env

COST PREDICTION

Run this before paid traffic:

python3 token_cost.py \
  --in 350 \
  --out 150 \
  --in-price 0.75 \
  --out-price 4.50 \
  --requests 200

DEPLOYMENT

1. Install the service:

sudo cp project12-donor-assistant.service \
  /etc/systemd/system/

2. Reload systemd:

sudo systemctl daemon-reload

3. Start the application:

sudo systemctl enable \
  --now \
  project12-donor-assistant.service

4. Check it:

sudo systemctl status \
  project12-donor-assistant.service \
  --no-pager

SMOKE TEST

bash smoke_test.sh

FIXED WORKLOAD

python3 run_workload.py \
  --requests 200 \
  --output-dir output

Review the summary:

cat output/workload_summary.json |
  python3 -m json.tool

REAL BILLING EVIDENCE

The untouched provider cost export is stored as:

billing/openai-cost-export.csv

The normalized summary used by finops_alerts.sh is:

billing/actual-cost-summary.csv

FINOPS CHECK

BILL_CSV=billing/actual-cost-summary.csv \
bash finops_alerts.sh \
  --budget 5 \
  --threshold 0.8 \
  --tag-key project \
  --days-elapsed 1

TOTAL REAL SPEND

The final real provider cost was:

$0.09276675
