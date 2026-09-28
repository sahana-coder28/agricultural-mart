import os
import re

def check_project():
    # 1. Check template references in routes/
    template_refs = set()
    routes_dir = 'routes'
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py'):
            with open(os.path.join(routes_dir, filename), 'r') as f:
                content = f.read()
                # Find all render_template calls
                matches = re.findall(r"render_template\( ?['\"]([^'\"]+)['\"]", content)
                for m in matches:
                    template_refs.add(m)

    print("\n--- Checking Template References ---")
    missing_templates = []
    for ref in template_refs:
        if not os.path.exists(os.path.join('templates', ref)):
            missing_templates.append(ref)
            print(f"MISSING: {ref} referenced in routes")
        else:
            print(f"OK: {ref}")

    # 2. Check url_for endpoints
    # First, collect all registered endpoints from routes
    registered_endpoints = set()
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py'):
            with open(os.path.join(routes_dir, filename), 'r') as f:
                content = f.read()
                # This is a bit complex, let's just look for @blueprint_name.route('/...')
                # and assume endpoint is function name
                bp_match = re.search(r"(\w+) = Blueprint\( ?['\"]([^'\"]+)['\"]", content)
                if bp_match:
                    bp_var = bp_match.group(1)
                    bp_name = bp_match.group(2)
                    # Find functions under @bp_var.route
                    route_matches = re.finditer(r"@" + bp_var + r"\.route\(.*?\)\ndef (\w+)\(", content)
                    for m in route_matches:
                        registered_endpoints.add(f"{bp_name}.{m.group(1)}")
    
    # Also check app.py for any routes
    if os.path.exists('app.py'):
        with open('app.py', 'r') as f:
            content = f.read()
            route_matches = re.finditer(r"@app\.route\(.*?\)\ndef (\w+)\(", content)
            for m in route_matches:
                registered_endpoints.add(f"main.{m.group(1)}") # simplified

    print("\n--- Checking Internal Links (url_for) ---")
    url_for_refs = set()
    # Check in templates/
    templates_dir = 'templates'
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.findall(r"url_for\( ?['\"]([^'\"]+)['\"]", content)
                    for m in matches:
                        url_for_refs.add(m)
    
    # Check in routes/
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py'):
            with open(os.path.join(routes_dir, filename), 'r') as f:
                content = f.read()
                matches = re.findall(r"url_for\( ?['\"]([^'\"]+)['\"]", content)
                for m in matches:
                    url_for_refs.add(m)

    missing_endpoints = []
    for ref in url_for_refs:
        # Ignore external or dynamic endpoints for now
        if '.' not in ref and ref != 'static':
            continue 
        if ref == 'static':
            continue
        if ref not in registered_endpoints:
            missing_endpoints.append(ref)
            print(f"MISSING ENDPOINT: {ref}")
        else:
            print(f"OK ENDPOINT: {ref}")

    # 3. Check for obvious errors in templates (missing extensions, etc)
    print("\n--- Checking Template Inheritance ---")
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    extend_match = re.search(r"{% extends ['\"]([^'\"]+)['\"]", content)
                    if extend_match:
                        base = extend_match.group(1)
                        if not os.path.exists(os.path.join('templates', base)):
                            print(f"MISSING BASE: {base} extended in {file}")

    print("\nProject Health Check Complete.")

if __name__ == "__main__":
    check_project()
