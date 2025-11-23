from openai import OpenAI

client = OpenAI()

# List all files
files = client.files.list().data

# Delete each file
for file in files:
    client.files.delete(file.id)
    print(f"Deleted file {file.id}")
