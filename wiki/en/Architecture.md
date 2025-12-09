
# RssBot System Architecture

The RssBot platform is designed based on a Hybrid Microservices architecture, aiming to provide maximum flexibility, stability, and scalability.

## Core Components

The RssBot architecture consists of two main parts:

1.  **Core Platform:** The brain of the system, located in the `src/rssbot/` path.
2.  **Services:** Independent functional units, each responsible for a specific task, located in the `services/` directory.

---

### 1. Core Platform

The core platform includes the following critical components that manage and coordinate the entire system:

#### **Core Controller**

-   **Path:** `src/rssbot/core/controller.py`
-   **Responsibility:** This controller is the beating heart of the platform. Its main task is Service Discovery, managing their lifecycle, and deciding how to route requests.
-   **Functionality:** On startup, the controller identifies all available services and, based on each service's configuration, decides whether to load it as an **In-Process Router** or communicate with it via a **REST API**.

#### **Cached Registry**

-   **Path:** `src/rssbot/discovery/cached_registry.py`
-   **Responsibility:** This component caches information about active services, their Health Status, and their Connection Method in Redis.
-   **Advantage:** By using Redis, service discovery is performed in under a millisecond, which significantly increases the speed of communication between services.

#### **ServiceProxy**

-   **Path:** `src/rssbot/discovery/proxy.py`
-   **Responsibility:** This class is an intelligent tool for communication between services. Developers can easily call methods of a target service without worrying about its implementation details.
-   **Functionality:** The `ServiceProxy` automatically queries the cached registry and selects the best communication method:
    -   **Router Mode:** If the target service is loaded as an internal router, its method is called directly without network overhead.
    -   **REST Mode:** If the service is running independently, the `ServiceProxy` sends an HTTP request to the corresponding endpoint.
    -   **Hybrid Mode:** A combination of the two modes above, maximizing flexibility.

---

### 2. Services

Each service is an independent FastAPI application that provides a specific functionality. This independence allows teams to develop and deploy their service without affecting other parts of the system.

**Examples of Services:**

-   **`channel_mgr_svc`:** Manages channels and RSS feeds.
-   **`ai_svc`:** Provides artificial intelligence capabilities like content summarization.
-   **`bot_svc`:** Communicates with the Telegram API and sends messages.
-   **`user_svc`:** Manages users and subscriptions.

This modular and flexible architecture makes RssBot a powerful platform ready for future developments.
