import re
from pathlib import Path

def test_dom_element_ids_exist_for_all_js_selectors():
    base_dir = Path(__file__).parent.parent
    for html_name in ["app/static/ko.html", "app/static/index.html"]:
        html_path = base_dir / html_name
        assert html_path.exists(), f"File {html_name} not found"
        content = html_path.read_text(encoding="utf-8")
        
        ids_in_js = re.findall(r"document\.getElementById\(['\"]([^'\"]+)['\"]\)", content)
        unique_ids = set(ids_in_js)
        
        # Exclude dynamic template IDs like votes-${feedbackId}
        checked_ids = [i for i in unique_ids if not i.startswith("votes-")]
        
        missing = []
        for elem_id in checked_ids:
            pattern = rf'id=["\']{re.escape(elem_id)}["\']'
            if not re.search(pattern, content):
                missing.append(elem_id)
                
        assert not missing, f"Missing DOM element IDs in {html_name}: {missing}"
