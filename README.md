# Kurator

A simple tool to collect data for machine learning models that help you write Kubernetes configurations.

## Usage

The tool is fairly simple to use. When you go to {url} (or `localhost:8000` if you run it locally), then you'll have an option to login with google:

![Login](./images/Login%20page.png)

After you login, you'll be redirected to the main page, where you can create/edit/delete/browse data points.

![Main page](./images/Main%20page.png)

Each data point is of the form **(Existing Config, Change Instruction, New Config)**.

The main page lets you enter such data. The left panel shows the "existing configuration", the right panel shows the "new configuration" and the bottom left panel shows the "change instruction". The difference between the two configurations is highlighted for easy viewing. For every data point you can also add notes, e.g., where you found the data point.

You can browse all data points by selecting the dropdown at top right.

## Setup

This is only relevant if you're setting up this tool.

1. Install [Docker](https://docs.docker.com/install/)
2. `cp .env.example .env` and fill in the values.
3. Run `unzip community-operators.zip` to unzip the community operators. If you don't run this, the first call to "validate" will take a long time.
4. Run `docker compose up --build` to start the server.

Data dumps are not stored in this repository. Fetch them from {secret location} and store it as `db/01_data_dump.sql` file. This data will only be loaded if `db/data` is empty. If you're trying to load new data, delete the `db/data` directory and run `docker compose up --build` again.
