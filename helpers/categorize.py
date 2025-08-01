import argparse
import os
from datetime import datetime
from glob import glob

import frontmatter
import yaml


def load_categories():
    cfg = yaml.safe_load(open("categories.yaml", "r"))
    return list(cfg.get("tier_1_categories", {}).keys())


def choose_category(text, categories):
    # TODO: replace with AI call or rule engine
    for cat in categories:
        if cat.lower() in text.lower():
            return cat
    return "uncategorized"


def categorize_file(path, categories):
    post = frontmatter.load(path)
    content = post.content
    cat = choose_category(content, categories)
    post["category"] = cat
    post["category_version"] = "v1.0"
    post["last_tagged_at"] = datetime.utcnow().isoformat() + "Z"
    post.metadata["tags"] = post.metadata.get("tags", []) + [cat]
    post.save(path)


def main(rerun_all=False, fix_missing=False, check=False, diff=False):
    categories = load_categories()
    md_files = glob("output/**/*.md", recursive=True)
    for f in md_files:
        post = frontmatter.load(f)
        exists = "category" in post.metadata
        if rerun_all or (fix_missing and not exists):
            categorize_file(f, categories)
        elif check:
            new_cat = choose_category(post.content, categories)
            if diff and new_cat != post.metadata.get("category"):
                print(f"[DIFF] {f}: {post.metadata.get('category')} -> {new_cat}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-all", action="store_true")
    parser.add_argument("--fix-missing", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--diff", action="store_true")
    args = parser.parse_args()
    main(**vars(args))
