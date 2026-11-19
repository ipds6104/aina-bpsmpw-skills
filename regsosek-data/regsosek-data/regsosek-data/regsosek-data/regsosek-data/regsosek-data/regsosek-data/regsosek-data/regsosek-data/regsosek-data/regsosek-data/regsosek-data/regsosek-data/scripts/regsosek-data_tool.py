#!/usr/bin/env python3
"""
regsosek-data_tool.py - High-Performance OLAP Query & Search Engine for Regsosek 2022 Mempawah Microdata.
Uses DuckDB to query Parquet datasets stored in shared_data/regsosek/.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SHARED_REGSOSEK = BASE_DIR / "shared_data" / "regsosek"
PARQUET_ART_LABELED = SHARED_REGSOSEK / "data_art_mempawah_labeled.parquet"
PARQUET_ART_FULL = SHARED_REGSOSEK / "data_art_mempawah_full.parquet"
PARQUET_KK_LABELED = SHARED_REGSOSEK / "data_kk_mempawah_labeled.parquet"
PARQUET_KK = SHARED_REGSOSEK / "data_kk_mempawah.parquet"


def get_duckdb_conn():
    try:
        import duckdb
    except ImportError:
        print(json.dumps({"status": "error", "message": "DuckDB is not installed."}, indent=2), file=sys.stderr)
        sys.exit(1)

    con = duckdb.connect(database=":memory:")
    # Register views if parquet files exist
    if PARQUET_ART_LABELED.exists():
        con.execute(f"CREATE OR REPLACE VIEW art AS SELECT * FROM '{PARQUET_ART_LABELED}'")
        con.execute(f"CREATE OR REPLACE VIEW art_labeled AS SELECT * FROM '{PARQUET_ART_LABELED}'")
    if PARQUET_ART_FULL.exists():
        con.execute(f"CREATE OR REPLACE VIEW art_full AS SELECT * FROM '{PARQUET_ART_FULL}'")
    if PARQUET_KK_LABELED.exists():
        con.execute(f"CREATE OR REPLACE VIEW kk AS SELECT * FROM '{PARQUET_KK_LABELED}'")
        con.execute(f"CREATE OR REPLACE VIEW kk_labeled AS SELECT * FROM '{PARQUET_KK_LABELED}'")
    if PARQUET_KK.exists():
        con.execute(f"CREATE OR REPLACE VIEW kk_raw AS SELECT * FROM '{PARQUET_KK}'")
    return con


def cmd_status(args):
    files = {}
    total_size = 0
    con = None

    if SHARED_REGSOSEK.exists():
        for p in SHARED_REGSOSEK.glob("*.parquet"):
            size = p.stat().st_size
            total_size += size
            files[p.name] = {
                "size_mb": round(size / (1024 * 1024), 2),
                "path": str(p)
            }

    # Fetch row counts if duckdb can connect
    if files:
        con = get_duckdb_conn()
        for name, info in files.items():
            try:
                cnt = con.execute(f"SELECT count(*) FROM '{info['path']}'").fetchone()[0]
                info["row_count"] = cnt
            except Exception as e:
                info["row_count_error"] = str(e)

    res = {
        "status": "ready" if files else "not_found",
        "skill": "regsosek-data",
        "shared_dir": str(SHARED_REGSOSEK),
        "parquet_files_count": len(files),
        "total_parquet_size_mb": round(total_size / (1024 * 1024), 2),
        "files": files,
        "views_available": ["art", "art_labeled", "art_full", "kk", "kk_labeled", "kk_raw"] if files else []
    }
    print(json.dumps(res, indent=2))


def cmd_query(args):
    sql = args.sql.strip()
    if not sql:
        print(json.dumps({"status": "error", "message": "SQL query is empty"}, indent=2))
        sys.exit(1)

    con = get_duckdb_conn()
    try:
        # Check if limit needed
        final_sql = sql
        if args.limit and not ("limit" in sql.lower()):
            final_sql = f"{sql} LIMIT {args.limit}"

        rel = con.execute(final_sql)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()

        if args.format == "table":
            # Pretty table text format
            print(f"Query: {final_sql}")
            print(f"Results: {len(rows)} row(s)\n")
            if not rows:
                print("No rows returned.")
                return
            col_widths = [max(len(str(c)), max(len(str(r[i])) for r in rows)) for i, c in enumerate(cols)]
            hdr = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(cols))
            sep = "-+-".join("-" * col_widths[i] for i in range(len(cols)))
            print(hdr)
            print(sep)
            for r in rows:
                print(" | ".join(str(r[i]).ljust(col_widths[i]) for i in range(len(cols))))
        elif args.format == "csv":
            import csv
            writer = csv.writer(sys.stdout)
            writer.writerow(cols)
            for r in rows:
                writer.writerow(r)
        else:
            # Default JSON
            dict_rows = [dict(zip(cols, r)) for r in rows]
            print(json.dumps({
                "status": "success",
                "row_count": len(dict_rows),
                "columns": cols,
                "rows": dict_rows
            }, indent=2, default=str))

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "sql": sql,
            "error": str(e)
        }, indent=2), file=sys.stderr)
        sys.exit(1)


def cmd_search_art(args):
    con = get_duckdb_conn()
    where_clauses = []
    params = []

    if args.nama:
        where_clauses.append("lower(nama_art) LIKE ?")
        params.append(f"%{args.nama.lower().strip()}%")
    if args.nik:
        where_clauses.append("nik LIKE ?")
        params.append(f"%{args.nik.strip()}%")
    if args.no_kk:
        where_clauses.append("no_kartu_keluarga LIKE ?")
        params.append(f"%{args.no_kk.strip()}%")
    if args.kec:
        where_clauses.append("lower(nama_kec) LIKE ?")
        params.append(f"%{args.kec.lower().strip()}%")
    if args.desa:
        where_clauses.append("lower(nama_desa) LIKE ?")
        params.append(f"%{args.desa.lower().strip()}%")
    if args.sls:
        where_clauses.append("lower(nama_sls) LIKE ?")
        params.append(f"%{args.sls.lower().strip()}%")

    if not where_clauses:
        print(json.dumps({
            "status": "error",
            "message": "Minimal satu filter pencarian (--nama, --nik, --no-kk, --kec, --desa, --sls) harus diberikan."
        }, indent=2))
        sys.exit(1)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT 
            nama_art,
            nik,
            no_kartu_keluarga,
            nama_kepala_keluarga,
            nama_kec,
            nama_desa,
            nama_sls,
            jenis_kelamin_label,
            umur,
            status_perkawinan_label,
            hub_kep_keluarga_label
        FROM art
        WHERE {where_sql}
        LIMIT {args.limit}
    """

    try:
        rel = con.execute(query, params)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        dict_rows = [dict(zip(cols, r)) for r in rows]
        print(json.dumps({
            "status": "success",
            "filter_applied": {
                "nama": args.nama,
                "nik": args.nik,
                "no_kk": args.no_kk,
                "kec": args.kec,
                "desa": args.desa,
                "sls": args.sls
            },
            "found_count": len(dict_rows),
            "rows": dict_rows
        }, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


def cmd_search_kk(args):
    con = get_duckdb_conn()
    where_clauses = []
    params = []

    if args.nama:
        where_clauses.append("lower(nama_kepala_keluarga) LIKE ?")
        params.append(f"%{args.nama.lower().strip()}%")
    if args.no_kk:
        where_clauses.append("no_kartu_keluarga LIKE ?")
        params.append(f"%{args.no_kk.strip()}%")
    if args.kec:
        where_clauses.append("lower(nama_kec) LIKE ?")
        params.append(f"%{args.kec.lower().strip()}%")
    if args.desa:
        where_clauses.append("lower(nama_desa) LIKE ?")
        params.append(f"%{args.desa.lower().strip()}%")
    if args.sls:
        where_clauses.append("lower(nama_sls) LIKE ?")
        params.append(f"%{args.sls.lower().strip()}%")

    if not where_clauses:
        print(json.dumps({
            "status": "error",
            "message": "Minimal satu filter pencarian (--nama, --no-kk, --kec, --desa, --sls) harus diberikan."
        }, indent=2))
        sys.exit(1)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT 
            nama_kepala_keluarga,
            no_kartu_keluarga,
            nama_kec,
            nama_desa,
            nama_sls,
            jumlah_art,
            status_bangunan_label,
            jenis_lantai_label,
            jenis_dinding_label,
            jenis_atap_label,
            sumber_penerangan_label
        FROM kk
        WHERE {where_sql}
        LIMIT {args.limit}
    """

    try:
        rel = con.execute(query, params)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        dict_rows = [dict(zip(cols, r)) for r in rows]
        print(json.dumps({
            "status": "success",
            "filter_applied": {
                "nama": args.nama,
                "no_kk": args.no_kk,
                "kec": args.kec,
                "desa": args.desa,
                "sls": args.sls
            },
            "found_count": len(dict_rows),
            "rows": dict_rows
        }, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


def cmd_rekap(args):
    con = get_duckdb_conn()
    by = args.by.lower().strip()

    if by == "kecamatan":
        sql = """
            SELECT 
                nama_kec,
                count(*) as total_kk,
                sum(try_cast(jumlah_art as integer)) as total_art
            FROM kk
            GROUP BY nama_kec
            ORDER BY total_kk DESC
        """
    elif by == "desa":
        where = f"WHERE lower(nama_kec) LIKE '%{args.kec.lower().strip()}%'" if args.kec else ""
        sql = f"""
            SELECT 
                nama_kec,
                nama_desa,
                count(*) as total_kk,
                sum(try_cast(jumlah_art as integer)) as total_art
            FROM kk
            {where}
            GROUP BY nama_kec, nama_desa
            ORDER BY nama_kec, total_kk DESC
        """
    elif by == "status_bangunan":
        sql = """
            SELECT 
                status_bangunan_label,
                count(*) as total_kk
            FROM kk
            GROUP BY status_bangunan_label
            ORDER BY total_kk DESC
        """
    else:
        print(json.dumps({"status": "error", "message": f"Opsi rekap '{by}' tidak dikenali. Pilihan: kecamatan, desa, status_bangunan"}, indent=2))
        sys.exit(1)

    try:
        rel = con.execute(sql)
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        dict_rows = [dict(zip(cols, r)) for r in rows]
        print(json.dumps({
            "status": "success",
            "rekap_by": by,
            "row_count": len(dict_rows),
            "rows": dict_rows
        }, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


def cmd_export(args):
    con = get_duckdb_conn()
    sql = args.sql.strip()
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df = con.execute(sql).fetchdf()
        if out_path.suffix.lower() == ".csv":
            df.to_csv(out_path, index=False)
        else:
            df.to_excel(out_path, index=False)

        print(json.dumps({
            "status": "success",
            "message": f"Query result successfully exported to {out_path}",
            "file": str(out_path),
            "rows_exported": len(df),
            "size_kb": round(out_path.stat().st_size / 1024, 2)
        }, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Regsosek 2022 Mempawah Microdata OLAP & Search Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Cek ketersediaan dan statistik berkas dataset Regsosek")
    p_status.set_defaults(func=cmd_status)

    # query
    p_query = subparsers.add_parser("query", help="Eksekusi SQL arbitrary DuckDB pada view 'art' atau 'kk'")
    p_query.add_argument("--sql", "-s", required=True, help="SQL query string")
    p_query.add_argument("--format", "-f", choices=["json", "table", "csv"], default="json", help="Format output")
    p_query.add_argument("--limit", "-l", type=int, default=50, help="Maksimal baris yang ditampilkan")
    p_query.set_defaults(func=cmd_query)

    # search-art
    p_art = subparsers.add_parser("search-art", help="Cari data individu/ART")
    p_art.add_argument("--nama", help="Nama ART (partial search)")
    p_art.add_argument("--nik", help="NIK")
    p_art.add_argument("--no-kk", help="No Kartu Keluarga")
    p_art.add_argument("--kec", help="Nama Kecamatan")
    p_art.add_argument("--desa", help="Nama Desa / Kelurahan")
    p_art.add_argument("--sls", help="Nama SLS / RT / Dusun")
    p_art.add_argument("--limit", "-l", type=int, default=20, help="Batas hasil (default: 20)")
    p_art.set_defaults(func=cmd_search_art)

    # search-kk
    p_kk = subparsers.add_parser("search-kk", help="Cari data keluarga/KK")
    p_kk.add_argument("--nama", help="Nama Kepala Keluarga (partial search)")
    p_kk.add_argument("--no-kk", help="No Kartu Keluarga")
    p_kk.add_argument("--kec", help="Nama Kecamatan")
    p_kk.add_argument("--desa", help="Nama Desa / Kelurahan")
    p_kk.add_argument("--sls", help="Nama SLS / RT / Dusun")
    p_kk.add_argument("--limit", "-l", type=int, default=20, help="Batas hasil (default: 20)")
    p_kk.set_defaults(func=cmd_search_kk)

    # rekap
    p_rekap = subparsers.add_parser("rekap", help="Rekapitulasi agregat KK & ART")
    p_rekap.add_argument("--by", choices=["kecamatan", "desa", "status_bangunan"], default="kecamatan", help="Dimensi agregasi")
    p_rekap.add_argument("--kec", help="Filter kecamatan untuk rekap desa")
    p_rekap.set_defaults(func=cmd_rekap)

    # export
    p_export = subparsers.add_parser("export", help="Ekspor hasil kueri ke file Excel (.xlsx) atau CSV")
    p_export.add_argument("--sql", "-s", required=True, help="SQL query yang akan diekspor")
    p_export.add_argument("--output", "-o", required=True, help="Path berkas output (.xlsx atau .csv)")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
