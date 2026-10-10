import shutil
import os

source_dir = r"C:\Users\kbarb\Documents\GitHub\tetherpad\build\exe.win-amd64-3.11"
output_filename = r"C:\Users\kbarb\Documents\GitHub\tetherpad\Output\TetherPad_v1.2.2.zip"

print(f"Creating zip file {output_filename} from {source_dir}...")
# shutil.make_archive creates the archive without the .zip extension in the name parameter
shutil.make_archive(output_filename.replace('.zip', ''), 'zip', source_dir)
print(f"Zip created successfully: {output_filename}")
print(f"Size: {os.path.getsize(output_filename) / (1024*1024):.2f} MB")
