import csv


def gen_db():
    print("Generating DB Setup...")
    with open("bic_directory.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerows(
            [
                ["BIC", "Name", "Country"],
                ["UKWLGB2LXXX", "UK World Link", "GB"],
                ["DEUTDEFFXXX", "Deutsche Efficiency", "DE"],
                ["SUDASDKHXXX", "Khartoum Bank", "SD"],
            ]
        )

    with open("graph_schema_setup.cypher", "w") as f:
        f.write(
            "CREATE CONSTRAINT uetr_uniq IF NOT EXISTS FOR (t:Transaction) REQUIRE t.uetr IS UNIQUE;"
        )
    print("✅ DB Setup Generated.")


if __name__ == "__main__":
    gen_db()
