from datetime import datetime, timezone, timedelta

def unix_to_ist(unix_timestamp):
    """Converts a UNIX timestamp to Indian Standard Time (IST)."""
    # Convert to UTC datetime
    utc_time = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    
    # Convert to IST (UTC+5:30)
    ist_offset = timedelta(hours=5, minutes=30)
    ist_time = utc_time + ist_offset
    
    # Return formatted IST time
    return ist_time.strftime("%Y-%m-%d %H:%M:%S IST")

# Example usage
timestamp = 1738235826
ist_time = unix_to_ist(timestamp)
print("IST Time:", ist_time)
