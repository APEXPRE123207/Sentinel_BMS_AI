import os
import json

def configure_idf():
    """Reads run_config.json, dynamically updates RunPeriod in small_office.idf, and outputs small_office_configured.idf."""
    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "..", "..", "run_config.json")
    
    if not os.path.exists(config_path):
        return None
        
    with open(config_path, "r") as f:
        cfg = json.load(f)
        
    if "simulation_start_date" not in cfg:
        return None
        
    month = cfg["simulation_start_date"].get("month", 7)
    day = cfg["simulation_start_date"].get("day", 7)
    day_of_week = cfg.get("day_of_week", "Tuesday")
    
    base_idf = cfg.get("base_idf_name", "small_office.idf")
    idfs_to_process = [base_idf, "baseline.idf"]
    
    for idf_name in idfs_to_process:
        base_idf_path = os.path.join(here, idf_name)
        if not os.path.exists(base_idf_path):
            continue
            
        configured_idf_path = os.path.join(here, idf_name.replace(".idf", "_configured.idf"))
            
        with open(base_idf_path, "r") as f:
            lines = f.readlines()
            
        in_run_period = False
        run_period_count = 0
        new_lines = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith("RunPeriod,"):
                in_run_period = True
                run_period_count += 1
                
            if in_run_period:
                if run_period_count == 1:
                    if "Begin Month" in line:
                        line = f"    {month},                       !- Begin Month\n"
                    elif "Begin Day of Month" in line:
                        line = f"    {day},                       !- Begin Day of Month\n"
                    elif "End Month" in line:
                        line = f"    {month},                       !- End Month\n"
                    elif "End Day of Month" in line:
                        line = f"    {day},                       !- End Day of Month\n"
                    elif "Day of Week for Start Day" in line:
                        line = f"    {day_of_week},                 !- Day of Week for Start Day\n"
                elif run_period_count == 2:
                    # Disable the winter run period if it exists by renaming it to something else or just setting it to the same date
                    pass
                    
            if ";" in line and in_run_period:
                in_run_period = False
                
            new_lines.append(line)
            
        with open(configured_idf_path, "w") as f:
            f.writelines(new_lines)
