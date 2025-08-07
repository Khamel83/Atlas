#!/usr/bin/env python3
"""
Migration Data Integrity Validator

Validates data integrity and completeness after Atlas-Podemos database migration.
Checks relationships, data consistency, and reports any issues found.

Usage:
    python3 database_integration/validate_migration.py [--db-path PATH]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("SQLAlchemy not found. Please run 'pip install sqlalchemy'")
    sys.exit(1)

class MigrationValidator:
    """Validates data integrity after database migration"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Validation results
        self.results = {
            'schema_validation': {},
            'data_integrity': {},
            'relationship_validation': {},
            'content_validation': {},
            'performance_metrics': {},
            'warnings': [],
            'errors': []
        }
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite"""
        
        print("🔍 DATABASE MIGRATION VALIDATION")
        print("=" * 60)
        print(f"📁 Database: {self.db_path}")
        
        if not self._validate_database_exists():
            return False
        
        # Run validation checks
        validation_checks = [
            ("Schema Validation", self._validate_schema),
            ("Data Integrity", self._validate_data_integrity),
            ("Relationship Validation", self._validate_relationships),
            ("Content Validation", self._validate_content_completeness),
            ("Performance Metrics", self._measure_performance)
        ]
        
        all_passed = True
        
        for check_name, check_function in validation_checks:
            print(f"\n🔧 {check_name}...")
            try:
                passed = check_function()
                if passed:
                    print(f"   ✅ {check_name} passed")
                else:
                    print(f"   ❌ {check_name} failed")
                    all_passed = False
            except Exception as e:
                print(f"   🚨 {check_name} error: {e}")
                self.results['errors'].append(f"{check_name}: {e}")
                all_passed = False
        
        self._print_validation_summary()
        return all_passed
    
    def _validate_database_exists(self) -> bool:
        """Check database file exists"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            return False
        return True
    
    def _validate_schema(self) -> bool:
        """Validate database schema structure"""
        
        required_tables = [
            'content_items', 
            'podcast_episodes',
            'processing_jobs',
            'content_analysis',
            'content_tags',
            'system_metadata'
        ]
        
        try:
            with self.engine.connect() as connection:
                # Check all required tables exist
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
                existing_tables = [row[0] for row in result.fetchall()]
                
                missing_tables = [table for table in required_tables if table not in existing_tables]
                
                self.results['schema_validation'] = {
                    'required_tables': len(required_tables),
                    'existing_tables': len(existing_tables),
                    'missing_tables': missing_tables,
                    'passed': len(missing_tables) == 0
                }
                
                if missing_tables:
                    self.results['errors'].append(f"Missing tables: {missing_tables}")
                    return False
                
                # Check indexes exist
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='index';"))
                indexes = [row[0] for row in result.fetchall()]
                self.results['schema_validation']['indexes_count'] = len(indexes)
                
                # Check triggers exist
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='trigger';"))
                triggers = [row[0] for row in result.fetchall()]
                self.results['schema_validation']['triggers_count'] = len(triggers)
                
                return True
                
        except Exception as e:
            self.results['errors'].append(f"Schema validation failed: {e}")
            return False
    
    def _validate_data_integrity(self) -> bool:
        """Validate data integrity constraints"""
        
        try:
            with self.engine.connect() as connection:
                # Check for NULL values in required fields
                null_checks = [
                    ("content_items", "uid", "Content items with NULL uid"),
                    ("content_items", "title", "Content items with NULL title"),
                    ("content_items", "content_type", "Content items with NULL content_type"),
                    ("podcast_episodes", "content_item_id", "Podcast episodes with NULL content_item_id"),
                    ("podcast_episodes", "original_audio_url", "Podcast episodes with NULL audio URL")
                ]
                
                null_violations = []
                for table, column, description in null_checks:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL;"))
                    count = result.fetchone()[0]
                    if count > 0:
                        null_violations.append(f"{description}: {count}")
                
                # Check for duplicate UIDs
                result = connection.execute(text("""
                    SELECT uid, COUNT(*) as count 
                    FROM content_items 
                    GROUP BY uid 
                    HAVING count > 1
                """))
                duplicate_uids = result.fetchall()
                
                # Check for orphaned podcast_episodes
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM podcast_episodes pe
                    LEFT JOIN content_items ci ON pe.content_item_id = ci.id
                    WHERE ci.id IS NULL
                """))
                orphaned_episodes = result.fetchone()[0]
                
                self.results['data_integrity'] = {
                    'null_violations': null_violations,
                    'duplicate_uids': len(duplicate_uids),
                    'orphaned_episodes': orphaned_episodes,
                    'passed': len(null_violations) == 0 and len(duplicate_uids) == 0 and orphaned_episodes == 0
                }
                
                if null_violations:
                    self.results['errors'].extend(null_violations)
                
                if duplicate_uids:
                    self.results['errors'].append(f"Duplicate UIDs found: {len(duplicate_uids)}")
                
                if orphaned_episodes > 0:
                    self.results['errors'].append(f"Orphaned podcast episodes: {orphaned_episodes}")
                
                return self.results['data_integrity']['passed']
                
        except Exception as e:
            self.results['errors'].append(f"Data integrity validation failed: {e}")
            return False
    
    def _validate_relationships(self) -> bool:
        """Validate foreign key relationships"""
        
        try:
            with self.engine.connect() as connection:
                # Count content items by type
                result = connection.execute(text("""
                    SELECT content_type, COUNT(*) as count
                    FROM content_items 
                    GROUP BY content_type
                """))
                content_by_type = dict(result.fetchall())
                
                # Count podcast episodes with content items
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM podcast_episodes pe
                    INNER JOIN content_items ci ON pe.content_item_id = ci.id
                    WHERE ci.content_type = 'podcast'
                """))
                podcast_episodes_linked = result.fetchone()[0]
                
                # Count total podcast content items
                podcast_content_count = content_by_type.get('podcast', 0)
                
                self.results['relationship_validation'] = {
                    'content_by_type': content_by_type,
                    'podcast_content_items': podcast_content_count,
                    'podcast_episodes_linked': podcast_episodes_linked,
                    'podcast_relationship_integrity': podcast_episodes_linked <= podcast_content_count,
                    'passed': True  # Will be set to False if issues found
                }
                
                # Check for issues
                if podcast_episodes_linked > podcast_content_count:
                    self.results['errors'].append(f"More podcast episodes ({podcast_episodes_linked}) than podcast content items ({podcast_content_count})")
                    self.results['relationship_validation']['passed'] = False
                
                return self.results['relationship_validation']['passed']
                
        except Exception as e:
            self.results['errors'].append(f"Relationship validation failed: {e}")
            return False
    
    def _validate_content_completeness(self) -> bool:
        """Validate content completeness and accessibility"""
        
        try:
            with self.engine.connect() as connection:
                # Count content by status
                result = connection.execute(text("""
                    SELECT status, COUNT(*) as count
                    FROM content_items 
                    GROUP BY status
                """))
                status_counts = dict(result.fetchall())
                
                # Check file accessibility for Atlas content
                result = connection.execute(text("""
                    SELECT file_path_html, file_path_markdown, file_path_metadata
                    FROM content_items 
                    WHERE content_type != 'podcast' 
                    AND (file_path_html IS NOT NULL OR file_path_markdown IS NOT NULL)
                    LIMIT 100
                """))
                
                atlas_files = result.fetchall()
                missing_files = []
                
                for file_row in atlas_files:
                    for file_path in file_row:
                        if file_path and not os.path.exists(file_path):
                            missing_files.append(file_path)
                
                # Check for content with errors
                result = connection.execute(text("""
                    SELECT COUNT(*) FROM content_items 
                    WHERE status = 'error' OR last_error IS NOT NULL
                """))
                error_count = result.fetchone()[0]
                
                self.results['content_validation'] = {
                    'status_counts': status_counts,
                    'total_content': sum(status_counts.values()),
                    'missing_files_sample': missing_files[:10],  # First 10 missing files
                    'missing_files_count': len(missing_files),
                    'content_with_errors': error_count,
                    'passed': len(missing_files) < 10 and error_count < (sum(status_counts.values()) * 0.1)  # Less than 10% errors
                }
                
                if len(missing_files) >= 10:
                    self.results['warnings'].append(f"Many Atlas files not found: {len(missing_files)} missing")
                
                if error_count > (sum(status_counts.values()) * 0.1):
                    self.results['warnings'].append(f"High error rate: {error_count} content items with errors")
                
                return self.results['content_validation']['passed']
                
        except Exception as e:
            self.results['errors'].append(f"Content validation failed: {e}")
            return False
    
    def _measure_performance(self) -> bool:
        """Measure database performance metrics"""
        
        try:
            with self.engine.connect() as connection:
                start_time = datetime.now()
                
                # Test query performance
                queries = [
                    ("Count all content", "SELECT COUNT(*) FROM content_items"),
                    ("Count by type", "SELECT content_type, COUNT(*) FROM content_items GROUP BY content_type"),
                    ("Recent content", "SELECT * FROM content_items ORDER BY created_at DESC LIMIT 10"),
                    ("Podcast episodes join", """
                        SELECT ci.title, pe.original_duration 
                        FROM content_items ci 
                        INNER JOIN podcast_episodes pe ON ci.id = pe.content_item_id 
                        WHERE ci.content_type = 'podcast' 
                        LIMIT 10
                    """)
                ]
                
                query_times = {}
                for query_name, query in queries:
                    query_start = datetime.now()
                    connection.execute(text(query)).fetchall()
                    query_time = (datetime.now() - query_start).total_seconds() * 1000  # ms
                    query_times[query_name] = round(query_time, 2)
                
                # Database file size
                db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
                
                total_time = (datetime.now() - start_time).total_seconds() * 1000
                
                self.results['performance_metrics'] = {
                    'database_size_mb': round(db_size_mb, 2),
                    'query_times_ms': query_times,
                    'total_validation_time_ms': round(total_time, 2),
                    'passed': all(time < 1000 for time in query_times.values())  # All queries under 1 second
                }
                
                slow_queries = [name for name, time in query_times.items() if time > 1000]
                if slow_queries:
                    self.results['warnings'].append(f"Slow queries detected: {slow_queries}")
                
                return self.results['performance_metrics']['passed']
                
        except Exception as e:
            self.results['errors'].append(f"Performance measurement failed: {e}")
            return False
    
    def _print_validation_summary(self):
        """Print comprehensive validation summary"""
        
        print(f"\n📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Schema results
        schema = self.results.get('schema_validation', {})
        print(f"📋 SCHEMA:")
        print(f"   Tables: {schema.get('existing_tables', 0)}/{schema.get('required_tables', 0)}")
        print(f"   Indexes: {schema.get('indexes_count', 0)}")
        print(f"   Triggers: {schema.get('triggers_count', 0)}")
        
        # Data integrity results
        integrity = self.results.get('data_integrity', {})
        print(f"\n🔒 DATA INTEGRITY:")
        print(f"   NULL violations: {len(integrity.get('null_violations', []))}")
        print(f"   Duplicate UIDs: {integrity.get('duplicate_uids', 0)}")
        print(f"   Orphaned episodes: {integrity.get('orphaned_episodes', 0)}")
        
        # Content results
        content = self.results.get('content_validation', {})
        print(f"\n📄 CONTENT:")
        print(f"   Total items: {content.get('total_content', 0)}")
        print(f"   Status breakdown: {content.get('status_counts', {})}")
        print(f"   Missing files: {content.get('missing_files_count', 0)}")
        print(f"   Items with errors: {content.get('content_with_errors', 0)}")
        
        # Relationship results
        relationships = self.results.get('relationship_validation', {})
        print(f"\n🔗 RELATIONSHIPS:")
        print(f"   Content by type: {relationships.get('content_by_type', {})}")
        print(f"   Podcast episodes linked: {relationships.get('podcast_episodes_linked', 0)}")
        
        # Performance results
        performance = self.results.get('performance_metrics', {})
        print(f"\n⚡ PERFORMANCE:")
        print(f"   Database size: {performance.get('database_size_mb', 0)} MB")
        print(f"   Query times: {performance.get('query_times_ms', {})}")
        
        # Warnings and errors
        if self.results['warnings']:
            print(f"\n⚠️  WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"   • {warning}")
        
        if self.results['errors']:
            print(f"\n🚨 ERRORS ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        # Overall result
        total_checks = 5
        passed_checks = sum([
            schema.get('passed', False),
            integrity.get('passed', False),
            relationships.get('passed', False),
            content.get('passed', False),
            performance.get('passed', False)
        ])
        
        success_rate = (passed_checks / total_checks) * 100
        print(f"\n🎯 OVERALL RESULT: {passed_checks}/{total_checks} checks passed ({success_rate:.1f}%)")
        
        if passed_checks == total_checks:
            print("🎉 ALL VALIDATIONS PASSED - Database migration successful!")
        elif passed_checks >= 3:
            print("⚠️  MIGRATION MOSTLY SUCCESSFUL - Review warnings above")
        else:
            print("❌ MIGRATION HAS ISSUES - Review errors above")

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Validate database migration integrity"
    )
    parser.add_argument(
        "--db-path",
        default="atlas_unified.db",
        help="Path to unified database (default: atlas_unified.db)"
    )
    parser.add_argument(
        "--json-output",
        help="Path to save validation results as JSON"
    )
    
    args = parser.parse_args()
    
    # Validate database exists
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        print("   Run migration scripts first to create and populate the database")
        return False
    
    # Run validation
    validator = MigrationValidator(args.db_path)
    success = validator.run_full_validation()
    
    # Save JSON output if requested
    if args.json_output:
        try:
            with open(args.json_output, 'w') as f:
                json.dump(validator.results, f, indent=2, default=str)
            print(f"\n💾 Validation results saved to {args.json_output}")
        except Exception as e:
            print(f"⚠️  Failed to save JSON output: {e}")
    
    if success or len(validator.results['errors']) == 0:
        print(f"\n🎉 SUCCESS: Database migration validation completed")
        return True
    else:
        print(f"\n❌ VALIDATION ISSUES FOUND: Check results above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)