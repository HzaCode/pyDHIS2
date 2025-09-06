"""Test data generator for DHIS2 API responses"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd


class TestDataGenerator:
    """Generate test data for DHIS2 API responses"""
    
    def __init__(self, seed: int = 42):
        """Initialize with a random seed for reproducible data"""
        random.seed(seed)
        self.seed = seed
    
    def generate_org_units(self, count: int = 10) -> List[Dict[str, str]]:
        """Generate organization unit test data"""
        org_units = []
        
        for i in range(count):
            org_units.append({
                "id": f"OU{i:03d}{uuid.uuid4().hex[:8]}",
                "name": f"Test Health Facility {i+1}",
                "code": f"HF_{i+1:03d}",
                "level": str(random.randint(3, 5)),
                "path": f"/ROOT/DISTRICT{random.randint(1,5)}/HF_{i+1:03d}"
            })
        
        return org_units
    
    def generate_data_elements(self, count: int = 5) -> List[Dict[str, str]]:
        """Generate data element test data"""
        element_names = [
            "BCG doses given",
            "DPT-HepB-Hib 1 doses given", 
            "DPT-HepB-Hib 3 doses given",
            "Measles doses given",
            "Polio 3 doses given"
        ]
        
        data_elements = []
        for i in range(min(count, len(element_names))):
            data_elements.append({
                "id": f"DE{i:03d}{uuid.uuid4().hex[:8]}",
                "name": element_names[i],
                "code": f"DE_{i+1:03d}",
                "valueType": "INTEGER"
            })
        
        return data_elements
    
    def generate_periods(self, start_year: int = 2023, months: int = 12) -> List[str]:
        """Generate period test data"""
        periods = []
        
        for month in range(1, months + 1):
            periods.append(f"{start_year}{month:02d}")
        
        return periods
    
    def generate_analytics_response(
        self,
        data_elements: List[Dict[str, str]],
        org_units: List[Dict[str, str]],
        periods: List[str],
        include_nulls: bool = True,
        null_rate: float = 0.1
    ) -> Dict[str, Any]:
        """Generate Analytics API response"""
        headers = [
            {"name": "dx", "column": "Data", "type": "TEXT"},
            {"name": "pe", "column": "Period", "type": "TEXT"},
            {"name": "ou", "column": "Organisation unit", "type": "TEXT"},
            {"name": "value", "column": "Value", "type": "NUMBER"}
        ]
        
        rows = []
        
        for de in data_elements:
            for period in periods:
                for ou in org_units:
                    # Generate realistic values
                    if include_nulls and random.random() < null_rate:
                        continue  # Skip this combination (null value)
                    
                    # Generate values based on data element type
                    if "BCG" in de["name"]:
                        value = str(random.randint(80, 120))
                    elif "DPT" in de["name"]:
                        value = str(random.randint(70, 110))
                    elif "Measles" in de["name"]:
                        value = str(random.randint(60, 100))
                    else:
                        value = str(random.randint(50, 150))
                    
                    rows.append([de["id"], period, ou["id"], value])
        
        return {
            "headers": headers,
            "rows": rows,
            "metaData": {
                "items": {},
                "dimensions": {}
            },
            "width": len(headers),
            "height": len(rows)
        }
    
    def generate_datavaluesets_response(
        self,
        data_elements: List[Dict[str, str]],
        org_units: List[Dict[str, str]],
        periods: List[str],
        include_conflicts: bool = False,
        conflict_rate: float = 0.05
    ) -> Dict[str, Any]:
        """Generate DataValueSets API response"""
        data_values = []
        
        for de in data_elements:
            for period in periods:
                for ou in org_units:
                    # Generate realistic values
                    if "BCG" in de["name"]:
                        value = str(random.randint(80, 120))
                    elif "DPT" in de["name"]:
                        value = str(random.randint(70, 110))
                    else:
                        value = str(random.randint(50, 150))
                    
                    data_value = {
                        "dataElement": de["id"],
                        "period": period,
                        "orgUnit": ou["id"],
                        "value": value,
                        "lastUpdated": datetime.now().isoformat(),
                        "created": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                        "storedBy": "test_user"
                    }
                    
                    data_values.append(data_value)
        
        return {"dataValues": data_values}
    
    def generate_tracker_events(
        self,
        program_id: str,
        program_stage_id: str,
        org_units: List[Dict[str, str]],
        event_count: int = 100
    ) -> Dict[str, Any]:
        """Generate Tracker events response"""
        events = []
        
        for i in range(event_count):
            org_unit = random.choice(org_units)
            event_date = datetime.now() - timedelta(days=random.randint(0, 365))
            
            event = {
                "event": f"EVENT{i:03d}{uuid.uuid4().hex[:8]}",
                "program": program_id,
                "programStage": program_stage_id,
                "orgUnit": org_unit["id"],
                "orgUnitName": org_unit["name"],
                "status": random.choice(["ACTIVE", "COMPLETED", "SCHEDULE"]),
                "occurredAt": event_date.isoformat(),
                "createdAt": event_date.isoformat(),
                "updatedAt": event_date.isoformat(),
                "dataValues": [
                    {
                        "dataElement": f"DE{j:03d}{uuid.uuid4().hex[:4]}",
                        "value": str(random.randint(1, 100))
                    }
                    for j in range(random.randint(1, 5))
                ]
            }
            
            events.append(event)
        
        return {
            "instances": events,
            "page": {
                "page": 1,
                "pageSize": event_count,
                "pageCount": 1,
                "total": event_count
            }
        }
    
    def generate_import_summary(
        self,
        total: int,
        imported: Optional[int] = None,
        updated: Optional[int] = None,
        ignored: Optional[int] = None,
        conflict_count: int = 0
    ) -> Dict[str, Any]:
        """Generate import summary response"""
        if imported is None:
            imported = int(total * 0.7)
        if updated is None:
            updated = int(total * 0.2)
        if ignored is None:
            ignored = total - imported - updated - conflict_count
        
        conflicts = []
        for i in range(conflict_count):
            conflicts.append({
                "object": f"CONFLICT{i:03d}",
                "property": "value",
                "value": "invalid_value",
                "message": f"Test conflict {i+1}",
                "errorCode": "E1234"
            })
        
        return {
            "status": "SUCCESS" if conflict_count == 0 else "WARNING",
            "imported": imported,
            "updated": updated,
            "ignored": ignored,
            "total": total,
            "conflicts": conflicts
        }
    
    def configure_endpoint(
        self,
        method: str,
        path: str,
        response_data: Dict[str, Any],
        status: int = 200,
        delay: float = 0.0,
        fail_count: int = 0
    ) -> None:
        """Configure a specific endpoint response"""
        full_path = f"/{method.lower()}{path}"
        self.responses[full_path] = MockResponse(
            status=status,
            data=response_data,
            delay=delay,
            fail_count=fail_count
        )
    
    async def start(self) -> str:
        """Start the mock server and return base URL"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        base_url = f"http://{self.host}:{self.port}"
        return base_url
    
    async def stop(self) -> None:
        """Stop the mock server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def get_base_url(self) -> str:
        """Get the server base URL"""
        return f"http://{self.host}:{self.port}"
