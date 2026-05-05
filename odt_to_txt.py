import zipfile
import re
import os

odt_path = r"c:\Users\soman\Desktop\a\somanqwop.odt"
txt_path = r"c:\Users\soman\Desktop\a\somanqwop.txt"

def extract_text_from_odt(odt_filepath, txt_filepath):
    try:
        # Read the content.xml from the zipped odt file
        with zipfile.ZipFile(odt_filepath, 'r') as z:
            content = z.read('content.xml').decode('utf-8')
        
        # Replace paragraph and heading tags with newlines to preserve some structure
        content = re.sub(r'</text:(p|h)>', '\n', content)
        
        # Remove all other XML tags
        text = re.sub(r'<[^>]+>', '', content)
        
        # Unescape common XML entities
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&apos;', "'")

        with open(txt_filepath, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print(f"Successfully extracted text to {txt_filepath}")
        return True
    except Exception as e:
        print(f"Error reading ODT file: {e}")
        return False

if __name__ == "__main__":
    extract_text_from_odt(odt_path, txt_path)
