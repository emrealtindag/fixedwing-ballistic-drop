file_path = r'mission_2\configs\mission2_fixedwing.yaml'
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        print(f.read())
except Exception as e:
    print(e)
