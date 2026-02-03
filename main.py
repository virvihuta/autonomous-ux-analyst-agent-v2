"""
Main Orchestrator - Web Reverse Engineering Agent with Smart Page Selection
Crawls everything, but only analyzes the most important pages
"""
import asyncio
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

from core.scout import Scout
from core.analyst import Analyst
from core.selector import PageSelector
from core.narrator import Narrator
from models.schemas import RebuildBlueprint, PageCluster
from utils.dom_processor import clean_dom_for_llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WebReverseEngineer:
    """
    Main orchestrator with smart page selection.
    
    Workflow:
    1. Scout crawls EVERYTHING (finds all links)
    2. Selector picks 10-20 most important pages
    3. Analyst analyzes ONLY selected pages (saves money!)
    4. Narrator describes only selected pages
    """
    
    def __init__(
        self,
        target_url: str,
        max_pages: int = 100,  # Increased - we want to find everything
        max_depth: int = 3,
        max_analyzed: int = 15,  # But only analyze top 15
        output_dir: str = "output",
        output_format: str = "markdown",
        enable_llm: bool = False,
        headless: bool = True
    ):
        self.target_url = target_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.max_analyzed = max_analyzed
        self.output_dir = Path(output_dir)
        self.output_format = output_format
        self.enable_llm = enable_llm
        self.headless = headless
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.scout = Scout(
            base_url=target_url,
            max_pages=max_pages,
            max_depth=max_depth,
            headless=headless
        )
        self.selector = PageSelector(max_selected=max_analyzed)
        self.analyst = Analyst(model="gpt-4")
        self.narrator = Narrator()
        
        # Store all discovered pages
        self.all_pages_file = self.output_dir / "all_discovered_pages.txt"
    
    async def run(self) -> RebuildBlueprint:
        """Execute the complete reverse-engineering workflow"""
        logger.info(f"🚀 Starting smart reverse-engineering for: {self.target_url}")
        logger.info(f"📊 Will crawl up to {self.max_pages} pages")
        logger.info(f"🎯 Will analyze top {self.max_analyzed} most important pages")
        logger.info(f"💰 Cost control: Only analyzing critical pages")
        
        # PHASE 1: Scout crawls EVERYTHING
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: SCOUT - Discovering All Pages")
        logger.info("="*80)
        
        all_clusters = await self.scout.crawl()
        
        # Save all discovered pages
        self._save_all_discovered_pages(all_clusters)
        logger.info(f"📝 Saved complete page list to: {self.all_pages_file}")
        
        # PHASE 2: Smart selection
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: SELECTOR - Choosing Important Pages")
        logger.info("="*80)
        
        selected_clusters = self.selector.select_important_pages(all_clusters)
        
        # PHASE 3: Analyze ONLY selected pages
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: ANALYST - Analyzing Selected Pages Only")
        logger.info("="*80)
        
        logger.info(f"🧠 Analyzing {len(selected_clusters)} pages (skipping {len(all_clusters) - len(selected_clusters)} redundant pages)")
        
        for cluster in selected_clusters:
            cleaned_html = ""
            network_logs = [ic.dict() for ic in cluster.network_intercepts]
            await self.analyst.analyze_cluster(cluster, cleaned_html, network_logs)
        
        # PHASE 4: Generate guide for selected pages only
        logger.info("\n" + "="*80)
        logger.info("PHASE 4: NARRATOR - Creating Reconstruction Guide")
        logger.info("="*80)
        
        # Create blueprint with only selected clusters
        blueprint = self._generate_blueprint(selected_clusters, all_clusters)
        
        # Save outputs
        output_files = self._save_outputs(blueprint)
        
        for file in output_files:
            logger.info(f"✅ Saved: {file}")
        
        # Print summary
        self._print_summary(blueprint, len(all_clusters))
        
        return blueprint
    
    def _save_all_discovered_pages(self, clusters: Dict[str, PageCluster]):
        """Save a list of ALL discovered pages"""
        
        with open(self.all_pages_file, 'w') as f:
            f.write(f"# All Discovered Pages on {self.target_url}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            f.write(f"# Total unique templates: {len(clusters)}\n")
            f.write(f"# Total pages: {sum(c.total_pages_in_cluster for c in clusters.values())}\n\n")
            
            for cluster in sorted(clusters.values(), key=lambda c: c.total_pages_in_cluster, reverse=True):
                f.write(f"\n## Template: {cluster.representative_url}\n")
                f.write(f"Pages using this template: {cluster.total_pages_in_cluster}\n")
                
                if len(cluster.sample_urls) > 1:
                    f.write("Sample URLs:\n")
                    for url in cluster.sample_urls:
                        f.write(f"  - {url}\n")
    
    def _generate_blueprint(self, selected_clusters: list, all_clusters: Dict[str, PageCluster]) -> RebuildBlueprint:
        """Generate blueprint from selected clusters"""
        
        stats = self.scout.get_statistics()
        
        from urllib.parse import urlparse
        domain = urlparse(self.target_url).netloc.replace('.', '_')
        project_name = f"{domain}_clone"
        
        blueprint = RebuildBlueprint(
            project_name=project_name,
            base_url=self.target_url,
            total_pages_crawled=stats['total_pages_crawled'],
            unique_clusters_found=len(all_clusters),  # Total found
            total_tokens_saved=stats['total_tokens_saved'],
            clusters=selected_clusters,  # Only selected ones
            statistics={
                'clustering_efficiency': stats['clustering_efficiency'],
                'timestamp': datetime.now().isoformat(),
                'total_templates_found': len(all_clusters),
                'templates_analyzed': len(selected_clusters),
                'templates_skipped': len(all_clusters) - len(selected_clusters),
                'analyst_calls': self.analyst.total_api_calls,
                'cost_report': self.analyst.get_cost_report(),
                'selection_reasons': self.selector.get_selection_summary()
            }
        )
        
        return blueprint
    
    def _save_outputs(self, blueprint: RebuildBlueprint) -> list:
        """Save blueprint in requested format(s)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{blueprint.project_name}_{timestamp}"
        
        saved_files = []
        
        # Save JSON (compact version with selected pages)
        if self.output_format in ['json', 'both']:
            json_path = self.output_dir / f"{base_filename}.json"
            with open(json_path, 'w') as f:
                json.dump(blueprint.dict(), f, indent=2)
            saved_files.append(json_path)
        
        # Save Markdown (human-readable guide)
        if self.output_format in ['markdown', 'both']:
            md_content = self.narrator.generate_reconstruction_guide(blueprint)
            md_path = self.output_dir / f"{base_filename}.md"
            with open(md_path, 'w') as f:
                f.write(md_content)
            saved_files.append(md_path)
        
        return saved_files
    
    def _print_summary(self, blueprint: RebuildBlueprint, total_clusters: int):
        """Print a summary of the results"""
        print("\n" + "="*80)
        print("📊 FINAL SUMMARY")
        print("="*80)
        print(f"Project: {blueprint.project_name}")
        print(f"URL: {blueprint.base_url}")
        print(f"\n🔍 Discovery Phase:")
        print(f"  Total pages crawled: {blueprint.total_pages_crawled}")
        print(f"  Unique templates found: {total_clusters}")
        print(f"\n🎯 Selection Phase:")
        print(f"  Templates analyzed: {len(blueprint.clusters)}")
        print(f"  Templates skipped: {total_clusters - len(blueprint.clusters)}")
        print(f"\n💰 Cost Savings:")
        print(f"  Pages not analyzed: {total_clusters - len(blueprint.clusters)}")
        print(f"  Estimated tokens saved: {blueprint.total_tokens_saved:,}")
        
        cost_report = blueprint.statistics.get('cost_report', {})
        print(f"  Total cost: ${cost_report.get('estimated_cost_usd', 0):.2f}")
        
        print("\n📋 Pages Selected for Analysis:")
        for cluster in blueprint.clusters:
            page_name = cluster.representative_url.split('/')[-1] or 'homepage'
            print(f"  ✓ {cluster.page_type}")
        
        print("="*80 + "\n")


async def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Smart Web Reverse Engineering - Analyzes only important pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Smart analysis (finds everything, analyzes top 15)
  python main.py https://example.com

  # Increase discovery (find more pages)
  python main.py https://example.com --max-pages 200

  # Analyze more pages
  python main.py https://example.com --max-analyzed 20

  # Quick test
  python main.py https://example.com --max-pages 20 --max-analyzed 10
        """
    )
    
    parser.add_argument(
        'url',
        help='Target website URL to analyze'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='Maximum pages to discover (default: 100)'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=3,
        help='Maximum link depth (default: 3)'
    )
    parser.add_argument(
        '--max-analyzed',
        type=int,
        default=15,
        help='Maximum pages to analyze in detail (default: 15)'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory (default: output/)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'both'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--enable-llm',
        action='store_true',
        help='Enable real LLM analysis'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser while crawling'
    )
    
    args = parser.parse_args()
    
    if not args.url.startswith(('http://', 'https://')):
        args.url = 'https://' + args.url
    
    engineer = WebReverseEngineer(
        target_url=args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        max_analyzed=args.max_analyzed,
        output_dir=args.output_dir,
        output_format=args.format,
        enable_llm=args.enable_llm,
        headless=not args.no_headless
    )
    
    try:
        await engineer.run()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
