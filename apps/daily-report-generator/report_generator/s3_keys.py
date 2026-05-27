def hourly_summary_key(output_prefix: str, hour: str) -> str:
    return f"{output_prefix}/intermediate/hourly/hh={hour}.json"


def processed_prefix(factory_id: str, dataset: str, dt) -> str:
    return (
        f"processed/{factory_id}/{dataset}/"
        f"yyyy={dt.year:04d}/mm={dt.month:02d}/dd={dt.day:02d}/hh={dt.hour:02d}/"
    )
