# EC2 registration and file portal

A Flask + SQLite assignment project for Ubuntu Server 24.04 LTS, served by Apache and mod_wsgi. This repository contains the application source, templates, styles, deployment configuration and tests.

## Deployed webpage

[Open the EC2 registration application](http://ec2-18-218-70-10.us-east-2.compute.amazonaws.com/)

The application was deployed for the assignment. Availability depends on the EC2 instance remaining running.

## Rubric coverage

| Requirement | Implementation / evidence to collect | Points |
| --- | --- | --- |
| Internet-accessible EC2 | Launch instance; record AMI, key pair name, network rules and public URL | 1 |
| Web server and database | Apache/mod_wsgi configuration, Flask application, SQLite users table | 1 |
| Share code | Submit this ZIP or your GitHub repository | 1 |
| Registration | Username and hashed password stored in SQLite | 1 |
| Basic details | First name, last name, email and address stored | 1 |
| Redirect and display | Successful registration redirects to `/profile` | 1 |
| Re-login | `/login` verifies credentials and retrieves the saved profile | 2 |
| File upload | Registration accepts `.txt`; SQLite stores original bytes, sanitized filename and word count; profile includes a download button | 2 |

Deployment screenshots and database verification are included in the separate assignment report.

## 1. Launch EC2

1. Sign in to the AWS console and open EC2 → Launch instance.
2. Name the instance `registration-assignment`.
3. Choose **Ubuntu Server 24.04 LTS (HVM)**. Select an architecture compatible with your chosen instance type. Check the Free Tier eligibility shown for your account; an eligible label alone does not guarantee zero charges.
4. Choose a suitable small instance type eligible under your account's plan.
5. Create a key pair, choose `.pem`, and download it. Keep the private key on your computer. Screenshot the key pair name, never the key contents.
6. Use a public subnet with a route to an internet gateway and enable **Auto-assign public IP**. The default VPC is a convenient option when available.
7. In the security group, allow **SSH / TCP 22 from My IP** and **HTTP / TCP 80 from Anywhere-IPv4 (`0.0.0.0/0`)**. Do not open port 5000; Apache serves the public application on port 80.
8. Launch, wait for Running and passing status checks, and record the Public IPv4 address and Public IPv4 DNS name.

Reference: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html

## 2. Copy the project from your Mac

Download and extract `EC2_Registration_Project.zip`. Open Terminal in the directory containing the extracted `ec2-registration` folder. Replace `YOUR_KEY.pem` and `YOUR_PUBLIC_DNS` with your actual values in every command. The Ubuntu AMI uses the SSH username `ubuntu`.

```bash
chmod 400 /path/to/YOUR_KEY.pem
scp -i /path/to/YOUR_KEY.pem -r ec2-registration ubuntu@YOUR_PUBLIC_DNS:~/
ssh -i /path/to/YOUR_KEY.pem ubuntu@YOUR_PUBLIC_DNS
```

## 3. Install on the EC2 instance

Run these commands in the connected EC2 terminal. They assume a new instance without an existing website at this location.

```bash
sudo mkdir -p /var/www
sudo cp -a ~/ec2-registration /var/www/ec2-registration
cd /var/www/ec2-registration
sudo bash deploy/setup.sh
```

The setup script installs `apache2`, `libapache2-mod-wsgi-py3`, `python3`, `python3-pip`, `python3-flask` and `sqlite3`; initializes the database; enables the supplied Apache site; disables the default Apache site; validates configuration; and starts Apache. It uses Ubuntu's Flask package, so system-wide pip installation is unnecessary.

Application source stays owned by root. Apache's `www-data` user can write only the `instance` directory, where the database and session key reside. The uploaded file is a SQLite BLOB, so no public upload directory is needed. The key persists across Apache restarts.

Flask/mod_wsgi reference: https://flask.palletsprojects.com/en/stable/deploying/mod_wsgi/

## 4. Verify server setup

```bash
python3 --version
python3 -m pip --version
python3 -c 'import flask; print(flask.__file__)'
sqlite3 --version
sudo apache2ctl -M
sudo apache2ctl configtest
sudo systemctl status apache2 --no-pager
curl -I http://127.0.0.1/
sudo sqlite3 /var/www/ec2-registration/instance/users.db '.schema users'
```

Check for `wsgi_module`, `Syntax OK`, an active Apache service, HTTP 200, and the `users` table. Take screenshots of the installation and these results.

## 5. Demonstrate the complete user experience

Open **`http://YOUR_PUBLIC_DNS/`** from your computer. You can also use `http://YOUR_PUBLIC_IP/` if public DNS is unavailable.

1. Use the supplied **sample/Limerick (1).txt**, copied unchanged from your attachment. It contains **32 words including the five-word title**, or 27 excluding the title. This app counts the full file and therefore displays **32**.
2. Register using a new username, an assignment-only password of at least eight characters, and sample first name, last name, email and address.
3. Use **Upload a text file** to select the actual Limerick file. Click **Create account & view profile**.
4. Confirm the browser redirects to `/profile`, displays all four personal details, and shows the uploaded filename and word count.
5. Click **Download your file**. Open the downloaded file and compare its contents with the original.
6. Click **Log out**. Enter an incorrect password to show the friendly error, then log in with the correct username/password. Confirm the saved profile, count and download remain available.
7. Check from another browser/private window that the public URL loads and that `/profile` requires login.

Word count uses `len(text.split())`: each whitespace-separated token counts as one word. Line breaks, tabs and repeated spaces act as separators; punctuation attached to a token does not add words. UTF-8 and UTF-8 with BOM are accepted. Empty files correctly show zero words. The exact uploaded bytes are returned on download; the filename is sanitized.

The file field is optional to allow basic registration testing. **Select the Limerick file during the graded demonstration** to demonstrate both file-related points. If you forget, create a fresh account with the file selected.

This follows the assignment's HTTP example. HTTP does not encrypt traffic: use sample personal information and a password you do not use elsewhere. A production deployment would also need HTTPS and login rate limiting.

## 6. Show saved data

After registering in the browser, run:

```bash
sudo sqlite3 -header -column /var/www/ec2-registration/instance/users.db \
  'SELECT id, username, firstname, lastname, email, address, filename, word_count, length(file_data) AS stored_bytes FROM users;'
```

This demonstrates saved profile details and uploaded bytes without printing password hashes. The schema uses `password_hash` instead of storing plain-text passwords. Queries use parameters to avoid SQL injection. Profile and download routes retrieve the currently authenticated user's record rather than trusting a username or user ID in the URL.

## 7. Screenshot and submission checklist

- [ ] EC2 launch settings: name, Ubuntu 24.04 AMI and instance type.
- [ ] Key pair selection/name and network settings.
- [ ] Security group inbound rules for SSH and HTTP.
- [ ] Running instance with passing status checks and public address.
- [ ] Connected EC2 terminal and dependency installation output.
- [ ] Apache virtual host configuration and `wsgi_module` enabled.
- [ ] Python, pip and SQLite verification; Apache status and config test.
- [ ] SQLite table schema and stored registration/file record.
- [ ] Registration form with personal details and selected Limerick file. Keep password masked.
- [ ] Profile after submission, showing all details, filename, word count and download button.
- [ ] Login page, incorrect-password feedback, and profile after successful re-login.
- [ ] Downloaded file opened and checked against the original.
- [ ] Code archive attached or GitHub URL accessible to grader.
- [ ] Exact working AWS URL included as text in the submission.

Submit this project ZIP as the permitted attachment, or upload its source files to your GitHub repository. Do not include `instance/`, database files, uploaded documents, private keys or session secrets in a public repository. The supplied `.gitignore` excludes these runtime files and keys.

Suggested submission text to fill in with real results:

> Webpage: http://[my actual EC2 public DNS]/
>
> Code: [attached ZIP or actual repository URL]
>
> Platform: Ubuntu Server 24.04 LTS, Apache with mod_wsgi, Python 3, Flask and SQLite3.
>
> Demonstration: registered a user with all required details and the provided Limerick file, viewed the profile and [actual count] words, downloaded the file, logged out and successfully logged back in.

Keep the instance running until grading is complete. If you stop/start it, the public address may change; recheck and update the submitted URL. Manage charges through your AWS account and clean up after the grading period.

## Troubleshooting

**Connection timeout:** confirm Running state, public IP, public-subnet routing and security-group HTTP port 80. Confirm the URL starts with `http://` for this configuration.

**Default Apache page:** verify `registration` is enabled and `000-default` disabled, then restart Apache.

**HTTP 500 / database permission error:** inspect the project-specific error log. The database directory must be owned by `www-data`, which needs directory write access as well as file access for SQLite journal files.

```bash
sudo tail -n 60 /var/log/apache2/registration-error.log
sudo tail -n 60 /var/log/apache2/error.log
sudo ls -ld /var/www/ec2-registration/instance
sudo ls -l /var/www/ec2-registration/instance
```

**Form expired:** reload the form and submit again. If server-side validation fails, the browser may require selecting the file again.

## Local testing, before deployment

On a computer with Python 3 and pip:

```bash
cd ec2-registration
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m unittest -v
python3 app.py
```

Open `http://127.0.0.1:5000/`. This local address is for development; submit the public AWS address after deploying.

The automated tests use a temporary SQLite database and synthetic text, covering registration, redirect, details, word count, byte-for-byte download, re-login, duplicate usernames, hashed passwords, empty/omitted files, isolation between users, CSRF rejection, invalid/oversized uploads and persistence across app recreation. The actual attached Limerick file was also tested separately: registration succeeded, the profile displayed 32 words, and the downloaded bytes matched the original exactly. These checks do not verify EC2 networking or Apache on your instance.
