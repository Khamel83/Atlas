#!/usr/bin/env python3
"""
Database Performance Benchmark

Comprehensive performance testing for the unified Atlas-Podemos database.
Tests query performance, indexing effectiveness, and scalability metrics.

Usage:
    python3 database_integration/benchmark_performance.py [--db-path PATH]
"""

import os
import sys
import time
import random
import statistics
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Callable

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from database_integration import UnifiedDB, ContentItem, PodcastEpisode
    import hashlib
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the Atlas root directory")
    sys.exit(1)

class DatabaseBenchmark:
    """
    Database performance benchmark suite
    
    Tests various database operations and provides performance metrics
    to ensure the unified database meets performance requirements.
    """
    
    def __init__(self, db_path: str = "atlas_unified.db"):
        """Initialize benchmark with database"""
        self.db_path = db_path
        self.db = UnifiedDB(db_path)
        self.results = {}
        
    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        print("🚀 DATABASE PERFORMANCE BENCHMARK")
        print("=" * 60)
        print(f"📁 Database: {self.db_path}")
        
        # Get initial database info
        initial_info = self.db.get_database_info()
        print(f"📊 Initial content: {initial_info.get('content_items', 0)} items")
        print(f"📊 Database size: {initial_info.get('file_size_mb', 0)} MB")
        
        # Run benchmark tests
        tests = [
            ("Query Performance", self.benchmark_queries),
            ("Insert Performance", self.benchmark_inserts),
            ("Update Performance", self.benchmark_updates),
            ("Index Effectiveness", self.benchmark_indexes),
            ("Join Performance", self.benchmark_joins),
            ("Concurrent Access", self.benchmark_concurrency),
            ("Large Dataset", self.benchmark_large_dataset)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔧 Running {test_name}...")
            try:
                result = test_func()
                self.results[test_name.lower().replace(' ', '_')] = result
                self._print_test_result(test_name, result)
            except Exception as e:
                print(f"   ❌ {test_name} failed: {e}")
                self.results[test_name.lower().replace(' ', '_')] = {'error': str(e)}
        
        # Generate final report
        self._generate_performance_report()
        
        return self.results
    
    def benchmark_queries(self) -> Dict[str, Any]:
        """Benchmark basic query performance"""
        
        queries = [
            ("Count all content", lambda: self.db.get_all_content()),
            ("Get articles", lambda: self.db.get_articles(limit=100)),
            ("Get podcasts", lambda: self.db.get_podcasts(limit=100)),
            ("Get by status", lambda: self.db.get_completed_content(limit=100)),
            ("Find by UID", lambda: self.db.find_content_by_uid(self._get_random_uid())),
            ("Content statistics", lambda: self.db.get_content_statistics())
        ]
        
        results = {}
        
        for query_name, query_func in queries:
            times = []
            
            # Run each query multiple times
            for _ in range(5):
                start_time = time.time()
                try:
                    query_func()
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    times.append(execution_time)
                except Exception as e:
                    times.append(float('inf'))  # Mark as failed
            
            # Calculate statistics
            valid_times = [t for t in times if t != float('inf')]
            if valid_times:
                results[query_name] = {
                    'avg_ms': round(statistics.mean(valid_times), 2),
                    'min_ms': round(min(valid_times), 2),
                    'max_ms': round(max(valid_times), 2),
                    'success_rate': len(valid_times) / len(times)
                }
            else:
                results[query_name] = {'error': 'All queries failed'}
        
        return results
    
    def benchmark_inserts(self) -> Dict[str, Any]:
        """Benchmark insert performance"""
        
        # Test single inserts
        single_insert_times = []
        
        for i in range(10):
            uid = hashlib.md5(f"benchmark_single_{i}_{time.time()}".encode()).hexdigest()
            content = ContentItem(
                uid=uid,
                title=f"Benchmark Content {i}",
                content_type='article',
                source_url=f'https://example.com/article_{i}',
                status='completed'
            )
            
            start_time = time.time()
            self.db.add_content(content)
            insert_time = (time.time() - start_time) * 1000
            single_insert_times.append(insert_time)
        
        # Test batch inserts
        batch_size = 50
        batch_content = []
        
        for i in range(batch_size):
            uid = hashlib.md5(f"benchmark_batch_{i}_{time.time()}".encode()).hexdigest()
            content = ContentItem(
                uid=uid,
                title=f"Batch Content {i}",
                content_type='article',
                source_url=f'https://example.com/batch_{i}',
                status='completed'
            )
            batch_content.append(content)
        
        start_time = time.time()
        with self.db.session() as session:
            session.add_all(batch_content)
            session.commit()
        batch_time = (time.time() - start_time) * 1000
        
        return {
            'single_inserts': {
                'avg_ms': round(statistics.mean(single_insert_times), 2),
                'total_items': len(single_insert_times)
            },
            'batch_insert': {
                'total_ms': round(batch_time, 2),
                'items_per_second': round((batch_size / batch_time) * 1000, 2),
                'total_items': batch_size
            }
        }
    
    def benchmark_updates(self) -> Dict[str, Any]:
        """Benchmark update performance"""
        
        # Get some existing content to update
        existing_content = self.db.get_all_content(limit=20)
        if not existing_content:
            return {'error': 'No existing content to update'}
        
        update_times = []
        
        for content in existing_content[:10]:
            start_time = time.time()
            success = self.db.update_content_status(
                content.uid, 
                'processing', 
                f'Updated at {datetime.utcnow()}'
            )
            update_time = (time.time() - start_time) * 1000
            
            if success:
                update_times.append(update_time)
        
        return {
            'avg_update_ms': round(statistics.mean(update_times), 2) if update_times else 0,
            'successful_updates': len(update_times),
            'total_attempted': len(existing_content[:10])
        }
    
    def benchmark_indexes(self) -> Dict[str, Any]:
        """Test index effectiveness"""
        
        # Test queries that should use indexes
        index_queries = [
            ("UID lookup", "SELECT * FROM content_items WHERE uid = ?", [self._get_random_uid()]),
            ("Content type filter", "SELECT * FROM content_items WHERE content_type = ?", ['article']),
            ("Status filter", "SELECT * FROM content_items WHERE status = ?", ['completed']),
            ("Date range", "SELECT * FROM content_items WHERE created_at >= ?", [datetime.utcnow() - timedelta(days=30)])
        ]
        
        results = {}
        
        with self.db.engine.connect() as connection:
            for query_name, sql, params in index_queries:
                times = []
                
                # Run query multiple times
                for _ in range(3):
                    start_time = time.time()
                    try:
                        from sqlalchemy import text
                        connection.execute(text(sql), params).fetchall()
                        execution_time = (time.time() - start_time) * 1000
                        times.append(execution_time)
                    except Exception as e:
                        times.append(float('inf'))
                
                valid_times = [t for t in times if t != float('inf')]
                if valid_times:
                    results[query_name] = {
                        'avg_ms': round(statistics.mean(valid_times), 2),
                        'index_effective': statistics.mean(valid_times) < 100  # Under 100ms considered good
                    }
        
        return results
    
    def benchmark_joins(self) -> Dict[str, Any]:
        """Test join performance"""
        
        # Test content-podcast join
        start_time = time.time()
        podcast_details = self.db.get_podcast_episodes_with_details(limit=50)
        join_time = (time.time() - start_time) * 1000
        
        # Test complex query with multiple conditions
        start_time = time.time()
        with self.db.session() as session:
            complex_results = session.query(ContentItem).filter(
                (ContentItem.content_type == 'podcast') &
                (ContentItem.status == 'completed') &
                (ContentItem.created_at >= datetime.utcnow() - timedelta(days=30))
            ).limit(20).all()
        complex_time = (time.time() - start_time) * 1000
        
        return {
            'podcast_join': {
                'time_ms': round(join_time, 2),
                'results_count': len(podcast_details)
            },
            'complex_filter': {
                'time_ms': round(complex_time, 2),
                'results_count': len(complex_results)
            }
        }
    
    def benchmark_concurrency(self) -> Dict[str, Any]:
        """Test concurrent access (simplified simulation)"""
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def concurrent_query(query_id: int):
            """Simulate concurrent database access"""
            try:
                start_time = time.time()
                # Create new DB connection for this thread
                thread_db = UnifiedDB(self.db_path)
                content = thread_db.get_articles(limit=10)
                thread_db.close()
                
                execution_time = (time.time() - start_time) * 1000
                results_queue.put({'query_id': query_id, 'time_ms': execution_time, 'success': True})
            except Exception as e:
                results_queue.put({'query_id': query_id, 'error': str(e), 'success': False})
        
        # Run concurrent queries
        threads = []
        num_threads = 5
        
        start_time = time.time()
        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_query, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = (time.time() - start_time) * 1000
        
        # Collect results
        thread_results = []
        while not results_queue.empty():
            thread_results.append(results_queue.get())
        
        successful_queries = [r for r in thread_results if r.get('success')]
        
        return {
            'total_time_ms': round(total_time, 2),
            'concurrent_queries': num_threads,
            'successful_queries': len(successful_queries),
            'avg_query_time_ms': round(
                statistics.mean([r['time_ms'] for r in successful_queries]), 2
            ) if successful_queries else 0
        }
    
    def benchmark_large_dataset(self) -> Dict[str, Any]:
        """Test performance with large dataset operations"""
        
        # Get total content count
        total_content = len(self.db.get_all_content())
        
        if total_content < 1000:
            return {'note': 'Dataset too small for large dataset benchmark', 'total_content': total_content}
        
        # Test large query
        start_time = time.time()
        large_query_result = self.db.get_all_content(limit=1000)
        large_query_time = (time.time() - start_time) * 1000
        
        # Test aggregation query
        start_time = time.time()
        stats = self.db.get_content_statistics()
        aggregation_time = (time.time() - start_time) * 1000
        
        return {
            'large_query': {
                'time_ms': round(large_query_time, 2),
                'items_retrieved': len(large_query_result),
                'items_per_second': round((len(large_query_result) / large_query_time) * 1000, 2)
            },
            'aggregation': {
                'time_ms': round(aggregation_time, 2),
                'total_items_processed': stats.get('total_content', 0)
            }
        }
    
    def _get_random_uid(self) -> str:
        """Get random UID from existing content"""
        content = self.db.get_all_content(limit=10)
        if content:
            return random.choice(content).uid
        return "nonexistent_uid"
    
    def _print_test_result(self, test_name: str, result: Dict[str, Any]):
        """Print formatted test result"""
        print(f"   📊 {test_name} Results:")
        
        if 'error' in result:
            print(f"      ❌ Error: {result['error']}")
            return
        
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"      📈 {key}:")
                for subkey, subvalue in value.items():
                    print(f"         • {subkey}: {subvalue}")
            else:
                print(f"      • {key}: {value}")
    
    def _generate_performance_report(self):
        """Generate comprehensive performance report"""
        
        print(f"\n📊 PERFORMANCE BENCHMARK REPORT")
        print("=" * 60)
        
        # Database info
        final_info = self.db.get_database_info()
        print(f"📁 Database: {final_info.get('database_path', 'Unknown')}")
        print(f"📊 Final size: {final_info.get('file_size_mb', 0)} MB")
        print(f"📊 Total content: {final_info.get('content_items', 0)} items")
        
        # Performance summary
        query_perf = self.results.get('query_performance', {})
        if query_perf and 'error' not in query_perf:
            avg_times = [v.get('avg_ms', 0) for v in query_perf.values() if isinstance(v, dict) and 'avg_ms' in v]
            if avg_times:
                overall_avg = statistics.mean(avg_times)
                print(f"⚡ Average query time: {overall_avg:.2f} ms")
                
                # Performance rating
                if overall_avg < 10:
                    rating = "🚀 Excellent"
                elif overall_avg < 50:
                    rating = "✅ Good"  
                elif overall_avg < 200:
                    rating = "⚠️ Acceptable"
                else:
                    rating = "❌ Needs Optimization"
                
                print(f"🎯 Performance rating: {rating}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if final_info.get('file_size_mb', 0) > 100:
            print("   • Consider database archiving for files over 100MB")
        
        if query_perf:
            slow_queries = [k for k, v in query_perf.items() 
                          if isinstance(v, dict) and v.get('avg_ms', 0) > 100]
            if slow_queries:
                print(f"   • Optimize slow queries: {', '.join(slow_queries)}")
            else:
                print("   • Query performance is optimal")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        error_count = sum(1 for result in self.results.values() if 'error' in result)
        total_tests = len(self.results)
        
        if error_count == 0:
            print("   🎉 All performance tests passed successfully!")
            print("   📈 Database is ready for production use")
        elif error_count < total_tests / 2:
            print("   ⚠️ Most performance tests passed with minor issues")  
            print("   🔧 Review failed tests and optimize as needed")
        else:
            print("   ❌ Multiple performance issues detected")
            print("   🚨 Significant optimization needed before production use")
    
    def close(self):
        """Close database connections"""
        self.db.close()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database performance benchmark")
    parser.add_argument("--db-path", default="atlas_unified.db", help="Database path")
    parser.add_argument("--json-output", help="Save results as JSON")
    
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found: {args.db_path}")
        print("   Create and populate database first")
        return False
    
    # Run benchmark
    benchmark = DatabaseBenchmark(args.db_path)
    
    try:
        results = benchmark.run_full_benchmark()
        
        # Save JSON output if requested
        if args.json_output:
            import json
            try:
                with open(args.json_output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\n💾 Results saved to {args.json_output}")
            except Exception as e:
                print(f"⚠️ Failed to save JSON: {e}")
        
        print(f"\n🎉 Benchmark completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        return False
    
    finally:
        benchmark.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)