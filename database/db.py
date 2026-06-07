import sqlite3
import hashlib
from datetime import datetime
from config import DB_PATH

class AnnouncementDB:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def init_db(self):
        """Database tables create karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                symbol TEXT UNIQUE,
                name TEXT,
                source TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY,
                source TEXT,
                company_name TEXT,
                symbol TEXT,
                announcement_datetime TIMESTAMP,
                subject TEXT,
                announcement_url TEXT,
                hash_id TEXT UNIQUE,
                is_result_related BOOLEAN,
                is_processed BOOLEAN DEFAULT 0,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                announcement_id INTEGER,
                doc_type TEXT,
                doc_url TEXT,
                local_path TEXT,
                download_status TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(announcement_id) REFERENCES announcements(id)
            )
        """)

        # Processing status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_status (
                id INTEGER PRIMARY KEY,
                announcement_id INTEGER,
                stage TEXT,
                status TEXT,
                error_msg TEXT,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(announcement_id) REFERENCES announcements(id)
            )
        """)

        conn.commit()
        conn.close()

    def insert_announcement(self, source, company_name, symbol, ann_datetime, 
                           subject, ann_url, is_result):
        """Announcement ko DB mein save karo"""
        # Generate unique hash
        hash_input = f"{source}_{company_name}_{subject}_{ann_datetime}"
        hash_id = hashlib.md5(hash_input.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO announcements 
                (source, company_name, symbol, announcement_datetime, subject, 
                 announcement_url, hash_id, is_result_related)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (source, company_name, symbol, ann_datetime, subject, 
                  ann_url, hash_id, is_result))

            conn.commit()
            ann_id = cursor.lastrowid
            print(f"✅ Announcement saved: {company_name} | ID: {ann_id}")
            return ann_id

        except sqlite3.IntegrityError:
            print(f"⚠️ Duplicate announcement: {hash_id}")
            return None
        finally:
            conn.close()

    def insert_document(self, announcement_id, doc_type, doc_url):
        """Document link ko save karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO documents 
            (announcement_id, doc_type, doc_url, download_status)
            VALUES (?, ?, ?, ?)
        """, (announcement_id, doc_type, doc_url, "pending"))

        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()

        print(f"📄 Document link saved: {doc_type} | ID: {doc_id}")
        return doc_id

    def get_pending_documents(self):
        """Download pending documents fetch karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.id, d.announcement_id, d.doc_type, d.doc_url, a.company_name
            FROM documents d
            JOIN announcements a ON d.announcement_id = a.id
            WHERE d.download_status = 'pending'
        """)

        rows = cursor.fetchall()
        conn.close()
        return rows

    def update_document_status(self, doc_id, status, local_path=None):
        """Document download status update karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE documents 
            SET download_status = ?, local_path = ?
            WHERE id = ?
        """, (status, local_path, doc_id))

        conn.commit()
        conn.close()

    def get_recent_announcements(self, limit=50):
        """Recent announcements fetch karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, source, company_name, symbol, announcement_datetime, 
                   subject, is_result_related
            FROM announcements
            ORDER BY announcement_datetime DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_unprocessed_announcements(self):
        """Process pending announcements fetch karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, source, company_name, symbol, subject
            FROM announcements
            WHERE is_processed = 0 AND is_result_related = 1
            ORDER BY announcement_datetime DESC
        """)

        rows = cursor.fetchall()
        conn.close()
        return rows

    def mark_announcement_processed(self, ann_id):
        """Announcement ko processed mark karo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE announcements 
            SET is_processed = 1
            WHERE id = ?
        """, (ann_id,))

        conn.commit()
        conn.close()

# Global DB instance
db = AnnouncementDB()
