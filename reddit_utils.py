from praw import Reddit

def get_reddit_posts(reddit: Reddit ,subreddits: list, limit:int) -> list:
        target = '+'.join(subreddits)
        
        posts = reddit.subreddit(target).hot(limit=limit)

        return posts
    


