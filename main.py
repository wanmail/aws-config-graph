


import time
import schedule
import logging

from datetime import datetime
from args import create_parser,run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_resources(args):
    try:
        logger.info(f"Starting collection at {datetime.now()}")
        
        run(args)
 
        logger.info(f"Collection completed at {datetime.now()}")
        
    except Exception as e:
        logger.error(f"Error during collection: {str(e)}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    try:
        run(args)
    except Exception as e:
        print(f'Error: {e}\n')
        parser.print_help()
        exit(1)
        
    if args.command == 'schedule':
        # Schedule daily collection
        schedule.every().day.at(args.schedule_time).do(collect_resources, args)
        logger.info(f"Scheduled daily collection at {args.schedule_time}")

        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        parser.print_help()
    
    


if __name__ == "__main__":
    main() 