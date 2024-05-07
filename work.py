import zipfile

with zipfile.ZipFile(r'three\excel_three_pictures.xlsx', 'r') as zip_ref:
    zip_ref.extractall(r'three')