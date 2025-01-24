from multiprocessing import cpu_count

import uvicorn


def main():
    workers: int = 2 * cpu_count() + 1
    config = uvicorn.Config("api.app:app", host="0.0.0.0", port=8081, workers=workers)
    server = uvicorn.Server(config)

    server.run()


if __name__ == "__main__":
    main()
