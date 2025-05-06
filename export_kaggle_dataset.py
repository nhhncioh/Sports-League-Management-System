import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import datetime
import json
import sqlite3

class KaggleDatasetExporter:
    def __init__(self, db_config):
        self.db_config = db_config
        self.engine = create_engine(
            f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        self.output_dir = "kaggle_dataset"
        self.metadata = {
            "title": "Top 5 European Football Leagues Dataset",
            "description": "Comprehensive dataset of top 5 European football leagues including matches, players, teams, and more.",
            "keywords": ["football", "soccer", "sports", "european leagues", "football-data.org"],
            "license": "CC0: Public Domain",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "source": "football-data.org API",
            "tables": []
        }

    def create_output_directory(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def export_to_sqlite(self):
        sqlite_path = os.path.join(self.output_dir, "sports_league.sqlite")

        # Create a new SQLite database
        conn = sqlite3.connect(sqlite_path)

        # List of tables to export
        tables = [
            "matches", "players", "teams", "leagues", "coaches",
            "referees", "stadiums", "standings", "scores", "seasons"
        ]

        for table in tables:
            print(f"Exporting {table} to SQLite...")
            query = f"SELECT * FROM {table}"
            df = pd.read_sql(query, self.engine)
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]

            # Convert list columns to JSON strings
            for col in df.select_dtypes(include='object').columns:
                if isinstance(df[col].iloc[0], list):  # Check if it's a list
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)

            df.to_sql(table, conn, if_exists='replace', index=False)

        conn.close()
        print(f"SQLite database saved to: {sqlite_path}")

    def export_table(self, table_name, query=None):
        if query:
            df = pd.read_sql(query, self.engine)
        else:
            df = pd.read_sql(f"SELECT * FROM {table_name}", self.engine)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Save to CSV
        output_file = os.path.join(self.output_dir, f"{table_name}.csv")
        df.to_csv(output_file, index=False)
        
        # Add table metadata
        self.metadata["tables"].append({
            "name": table_name,
            "rows": len(df),
            "columns": len(df.columns),
            "description": self.get_table_description(table_name)
        })
        
        return df

    def get_table_description(self, table_name):
        descriptions = {
            "matches": "Contains all match information including scores, dates, and teams",
            "players": "Player information including personal details and team affiliations",
            "teams": "Team information including names, leagues, and statistics",
            "leagues": "League information including country and competition details",
            "coaches": "Coach information including team affiliations",
            "referees": "Referee information for matches",
            "stadiums": "Stadium information including capacity and location",
            "scores": "Detailed match scores and statistics",
            "seasons": "Season information and competition details"
        }
        return descriptions.get(table_name, f"Data from {table_name} table")

    def export_all_tables(self):
        self.create_output_directory()

        # Export main tables
        tables = [
            "matches", "players", "teams", "leagues", "coaches",
            "referees", "stadiums", "standings", "scores", "seasons"
        ]

        for table in tables:
            print(f"Exporting {table}...")
            self.export_table(table)

        # Export SQLite version
        self.export_to_sqlite()

        # Save metadata and README
        with open(os.path.join(self.output_dir, "dataset-metadata.json"), "w") as f:
            json.dump(self.metadata, f, indent=2)

        self.create_readme()

    def create_readme(self):
        readme_content = f"""# Top 5 European Football Leagues Dataset

## Overview
This dataset contains comprehensive information about the top 5 European football leagues, sourced from football-data.org API.

## Dataset Information
- Last Updated: {self.metadata['last_updated']}
- Source: {self.metadata['source']}
- License: {self.metadata['license']}

## Tables
"""
        for table in self.metadata["tables"]:
            readme_content += f"""
### {table['name'].title()}
- Rows: {table['rows']}
- Columns: {table['columns']}
- Description: {table['description']}
"""

        with open(os.path.join(self.output_dir, "README.md"), "w") as f:
            f.write(readme_content)

if __name__ == "__main__":
    # Database configuration
    db_config = {
        "host": "localhost",
        "port": "5432",
        "database": "sports_league",
        "user": "sports_league_owner",
        "password": "postgres"  # Replace with actual password
    }
    
    exporter = KaggleDatasetExporter(db_config)
    exporter.export_all_tables() 