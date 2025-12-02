/**
 * Unsafe Code Lab - E2E Test Utilities
 *
 * Clean, minimal API for readable e2e tests with `?? js ... == ...` assertions.
 *
 * Response assertions:
 *   ?? js $(response).status() == 200
 *   ?? js $(response).hasOnlyUserData("plankton") == true
 *
 * Auth headers (pure functions):
 *   Authorization: {{auth.basic("plankton")}}
 *
 * Platform setup (makes HTTP requests):
 *   {{
 *     await platform.seed({plankton: 200, squidward: 150});
 *     const cookie = await auth.login("plankton");
 *     exports.sessionCookie = cookie;
 *   }}
 *
 *   Cookie: {{sessionCookie}}
 */

const crypto = require("crypto");
const MAILPIT_BASE = process.env.MAILPIT_URL || "http://127.0.0.1:8025/api/v1";

// ============================================================================
// DATA
// ============================================================================

const USERS = {
  sandy: {
    shortId: "sandy",
    email: "sandy@bikinibottom.sea",
    password: "fullStackSquirr3l!",
    displayName: "Sandy Cheeks",
    role: "admin",
    id: 1,
  },
  patrick: {
    shortId: "patrick",
    email: "patrick@bikinibottom.sea",
    password: "mayonnaise",
    displayName: "Patrick Star",
    role: "customer",
    id: 2,
  },
  plankton: {
    shortId: "plankton",
    email: "plankton@chum-bucket.sea",
    password: "i_love_my_wife",
    displayName: "Sheldon Plankton",
    role: "customer",
    id: 3,
  },
  spongebob: {
    shortId: "spongebob",
    email: "spongebob@krusty-krab.sea",
    password: "EmployeeOfTheMonth",
    displayName: "SpongeBob SquarePants",
    role: "customer",
    id: 4,
  },
  mrkrabs: {
    shortId: "mrkrabs",
    email: "mr.krabs@krusty-krab.sea",
    password: "m$n$y",
    displayName: "Eugene Krabs",
    role: "restaurant_owner",
    id: 5,
  },
  squidward: {
    shortId: "squidward",
    email: "squidward@krusty-krab.sea",
    password: "clarinet4life",
    displayName: "Squidward Tentacles",
    role: "employee",
    id: 6,
  },
  karen: {
    shortId: "karen",
    email: "karen@chum-bucket.sea",
    password: "01001011",
    displayName: "Karen Plankton",
    role: "customer",
    id: 7,
  },
};

const ORG_KEYS = {
  krusty_krab: "key-krusty-krub-z1hu0u8o94",
  chum_bucket: "key-chum-bucket-b5kg32z1je",
  admin: "key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc",
};

const E2E_API_KEY = "e2e-test-key-unsafe-code-lab";

// Version-aware menu - v100: MVP with 3 combo meals
const MENU_V100 = {
  1: { id: "1", name: "Krabby Patty Combo", price: 12.99, category: "combo" },
  2: { id: "2", name: "Coral Bits Meal", price: 8.99, category: "combo" },
  3: {
    id: "3",
    name: "Triple Krabby Supreme",
    price: 18.99,
    category: "combo",
  },
};

// Version-aware menu - v101+: Full menu with individual items
const MENU_V101_PLUS = {
  ...MENU_V100,
  4: { id: "4", name: "Krabby Patty", price: 3.99, category: "main" },
  5: { id: "5", name: "Fries", price: 2.49, category: "side" },
  6: { id: "6", name: "Kelp Shake", price: 3.49, category: "drink" },
  7: { id: "7", name: "Coral Bits", price: 4.49, category: "side" },
  8: {
    id: "8",
    name: "Ultimate Krabby Feast",
    price: 27.99,
    category: "premium",
  },
};

// Version-aware menu - v301+: Multi-restaurant with availability tracking
const MENU_V301_PLUS = {
  // Krusty Krab menu (restaurant_id: 1)
  1: {
    id: "1",
    name: "Krabby Patty Combo",
    price: 12.99,
    restaurant_id: 1,
    available: false,
    category: "combo",
  },
  2: {
    id: "2",
    name: "Coral Bits Meal",
    price: 8.99,
    restaurant_id: 1,
    available: false,
    category: "combo",
  },
  3: {
    id: "3",
    name: "Triple Krabby Supreme",
    price: 18.99,
    restaurant_id: 1,
    available: false,
    category: "combo",
  },
  4: {
    id: "4",
    name: "Krabby Patty",
    price: 3.99,
    restaurant_id: 1,
    available: true,
    category: "main",
  },
  5: {
    id: "5",
    name: "Fries",
    price: 2.49,
    restaurant_id: 1,
    available: true,
    category: "side",
  },
  6: {
    id: "6",
    name: "Kelp Shake",
    price: 3.49,
    restaurant_id: 1,
    available: true,
    category: "drink",
  },
  7: {
    id: "7",
    name: "Coral Bits",
    price: 4.49,
    restaurant_id: 1,
    available: true,
    category: "side",
  },
  8: {
    id: "8",
    name: "Ultimate Krabby Feast",
    price: 27.99,
    restaurant_id: 1,
    available: true,
    category: "premium",
  },
  // Chum Bucket menu (restaurant_id: 2)
  9: {
    id: "9",
    name: "Chum Burger",
    price: 2.99,
    restaurant_id: 2,
    available: true,
    category: "main",
  },
  10: {
    id: "10",
    name: "ChumBalaya",
    price: 15.99,
    restaurant_id: 2,
    available: true,
    category: "premium",
  },
};

// ============================================================================
// CONFIG
// ============================================================================

function getConfig() {
  const version = process.env.VERSION || "v101";
  const versionNum = parseInt(version.substring(1));

  return {
    version,
    versionNum,
    baseUrl: process.env.BASE_URL || "http://localhost:8000/api",
    usesEmails: versionNum >= 106,
    hasSessions: versionNum >= 201,
    hasMultiRestaurant: versionNum >= 203,
    hasDatabase: versionNum >= 301,
  };
}

/**
 * Get the appropriate menu for the current version
 * v100: 3 combo meals only
 * v101-v202: Full menu with individual items
 * v301+: Multi-restaurant menu with availability tracking
 */
function getMenu() {
  const config = getConfig();
  const versionNum = config.versionNum;

  if (versionNum < 101) return { ...MENU_V100 };
  if (versionNum < 301) return { ...MENU_V101_PLUS };
  return { ...MENU_V301_PLUS };
}

// ============================================================================
// USER
// ============================================================================

function user(name) {
  const u = USERS[name.toLowerCase()];
  if (!u) {
    throw new Error(
      `Unknown user: ${name}. Available: ${Object.keys(USERS).join(", ")}`
    );
  }

  const config = getConfig();
  const username = config.usesEmails ? u.email : u.shortId;
  const userId = config.hasDatabase ? u.id : username;

  return {
    name: name.toLowerCase(),
    displayName: u.displayName,
    email: u.email,
    shortId: u.shortId,
    password: u.password,
    role: u.role,
    username, // Username for authentication
    id: userId, // User ID for database operations

    /**
     * Check if user can login with given password (defaults to correct password).
     * For predefined users in USERS database.
     *
     * Example:
     *   ?? js await user("plankton").canLogin() == true
     *   ?? js await user("plankton").canLogin("wrongpw") == false
     */
    async canLogin(password = null) {
      const pw = password ?? u.password;
      try {
        const resp = await fetch(
          `${config.baseUrl}/${config.version}/auth/login`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: u.email, password: pw }),
          }
        );
        return resp.ok;
      } catch {
        return false;
      }
    },

    /**
     * Get user's current balance.
     *
     * Example:
     *   ?? js await user("plankton").balance() == 200
     */
    async balance() {
      const basicHeader = `Basic ${Buffer.from(`${username}:${u.password}`).toString("base64")}`;
      const resp = await fetch(
        `${config.baseUrl}/${config.version}/account/credits`,
        {
          headers: { Authorization: basicHeader },
        }
      );
      if (!resp.ok) {
        throw new Error(`user("${name}").balance() failed: ${resp.status}`);
      }
      const body = await resp.json().catch(() => ({}));
      const val = body?.balance ?? body?.data?.balance;
      return parseFloat(val);
    },
  };
}


// ============================================================================
// AUTH
// ============================================================================

const auth = {
  // Basic Auth header (version-aware)
  // Example: Authorization: {{auth.basic("plankton")}}
  //          Authorization: {{auth.basic("plankton", "wrongpassword")}}  // test wrong pw
  basic(userName, password = null) {
    const config = getConfig();
    const u = user(userName);
    const pw = password ?? u.password;
    const credentials = config.usesEmails
      ? `${u.email}:${pw}`
      : `${u.shortId}:${pw}`;
    return `Basic ${Buffer.from(credentials).toString("base64")}`;
  },

  // Session login request body (for manual POST)
  // Example: POST /auth/login
  //          Content-Type: application/json
  //          {{auth.sessionLogin("plankton")}}
  sessionLogin(userName) {
    const u = user(userName);
    return JSON.stringify({
      email: u.email,
      password: u.password,
    });
  },

  /**
   * Login and get session cookie (makes actual HTTP request)
   * Returns cookie string ready for Cookie: {{cookie}} header
   *
   * Example:
   *   {{
   *     const cookie = await auth.login("plankton");
   *     exports.sessionCookie = cookie;
   *   }}
   *
   *   GET {{base}}/orders
   *   Cookie: {{sessionCookie}}
   */
  async login(userName) {
    const config = getConfig();
    const u = user(userName);

    const response = await fetch(
      `${config.baseUrl}/${config.version}/auth/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: u.email,
          password: u.password,
        }),
      }
    );

    if (response.status >= 400) {
      throw new Error(
        `auth.login() failed for ${userName}: ${response.status}`
      );
    }

    // Extract Set-Cookie header
    const setCookie = response.headers.get("set-cookie");
    if (!setCookie) {
      throw new Error("auth.login() got no Set-Cookie header");
    }

    return setCookie;
  },

  // Restaurant API key (org or user)
  // Example: X-API-Key: {{auth.restaurant("krusty_krab")}}
  //          X-API-Key: {{auth.restaurant("chum_bucket")}}
  restaurant(nameOrKey) {
    const config = getConfig();
    const normalized = nameOrKey.toLowerCase().replace(/[\s_-]/g, "_");

    // Try as org name first
    if (ORG_KEYS[normalized]) {
      return ORG_KEYS[normalized];
    }

    throw new Error(
      `No restaurant key for: "${nameOrKey}"\r\n` +
        `Available: ${Object.keys(ORG_KEYS).join(", ")}`
    );
  },

  // Admin/platform key
  // Example: X-Admin-API-Key: {{auth.admin()}}
  admin() {
    return ORG_KEYS.admin;
  },
};

// ============================================================================
// MENU
// ============================================================================

const menu = {
  // Get item by ID or name (version-aware)
  item(idOrName) {
    const MENU = getMenu();
    const key = String(idOrName);
    if (MENU[key]) return { ...MENU[key] };

    const byName = Object.values(MENU).find(
      (item) => item.name.toLowerCase() === key.toLowerCase()
    );
    if (byName) return { ...byName };

    throw new Error(`Menu item not found: ${idOrName}`);
  },

  // Get all items (version-aware)
  all() {
    const MENU = getMenu();
    return Object.values(MENU).map((item) => ({ ...item }));
  },

  // Find cheapest (version-aware)
  cheapest() {
    const MENU = getMenu();
    return Object.values(MENU).reduce((min, item) =>
      item.price < min.price ? item : min
    );
  },

  // Find most expensive (version-aware)
  expensive() {
    const MENU = getMenu();
    return Object.values(MENU).reduce((max, item) =>
      item.price > max.price ? item : max
    );
  },

  // Find by category (version-aware)
  category(cat) {
    const MENU = getMenu();
    return Object.values(MENU).filter((item) => item.category === cat);
  },

  // Calculate total for item IDs
  total(itemIds) {
    if (!Array.isArray(itemIds)) itemIds = [itemIds];
    return itemIds.reduce((sum, id) => {
      const item = this.item(id);
      return sum + parseFloat(item.price);
    }, 0.0);
  },

  // Find by criteria: {category: 'side', price: {min: 5, max: 10}} (version-aware)
  find(criteria) {
    const MENU = getMenu();
    let items = Object.values(MENU);

    if (criteria.category) {
      items = items.filter((i) => i.category === criteria.category);
    }

    if (criteria.price) {
      const { min = 0, max = Infinity } = criteria.price;
      items = items.filter((i) => i.price >= min && i.price <= max);
    }

    return items;
  },

  // Filter items (version-aware)
  // Example: menu.filter(item => item.available && item.restaurant_id === 1)
  filter(fn) {
    const MENU = getMenu();
    return Object.values(MENU).filter(fn);
  },

  /**
   * First available item for restaurant (v301+ only)
   * Example: menu.firstAvailable(1).id
   */
  firstAvailable(restaurantId = 1) {
    const MENU = getMenu();
    const entry = Object.values(MENU).find(
      (i) => i.restaurant_id == restaurantId && i.available
    );
    if (!entry) {
      throw new Error(`No available items for restaurant ${restaurantId}`);
    }
    return entry;
  },

  /**
   * First unavailable item for restaurant (v301+ only)
   * Example: menu.firstUnavailable(1).id
   */
  firstUnavailable(restaurantId = 1) {
    const MENU = getMenu();
    const entry = Object.values(MENU).find(
      (i) => i.restaurant_id == restaurantId && !i.available
    );
    if (!entry) {
      throw new Error(`No unavailable items for restaurant ${restaurantId}`);
    }
    return entry;
  },
};

// ============================================================================
// RESPONSE WRAPPER $(response)
// ============================================================================

function $(thing) {
  // Extract data and status
  let data;
  let statusCode;

  if (thing && typeof thing === "object") {
    if ("parsedBody" in thing || "statusCode" in thing || "status" in thing) {
      data = thing.parsedBody;
      statusCode = thing.statusCode ?? thing.status;
    } else {
      data = thing;
    }
  } else {
    data = thing;
  }

  const config = getConfig();
  const isArray = Array.isArray(data);
  const items = isArray ? data : data ? [data] : [];

  return {
    // Status
    status() {
      return statusCode ?? 0;
    },

    isOk() {
      return statusCode >= 200 && statusCode < 300;
    },

    isError() {
      return statusCode >= 400;
    },

    // Data access
    body() {
      return data;
    },

    isEmpty() {
      if (!data) return true;
      if (Array.isArray(data)) return data.length === 0;
      return Object.keys(data).length === 0;
    },

    count() {
      return isArray ? data.length : data ? 1 : 0;
    },

    // Field access
    field(fieldName) {
      if (!data) return undefined;
      if (isArray) return data[0]?.[fieldName];
      return data[fieldName];
    },

    hasFields(...fields) {
      if (!data) return false;

      if (isArray) {
        if (data.length === 0) return false;
        return data.every((item) => fields.every((field) => field in item));
      }

      return fields.every((field) => field in data);
    },

    hasField(field) {
      return this.hasFields(field);
    },

    fieldEquals(field, value) {
      return this.field(field) === value;
    },

    // User data validation
    hasOnlyUserData(userName) {
      if (!data) return false;

      const u = user(userName);
      const allowedIds = [u.id, u.username];

      return items.every((item) => {
        const itemUserId = item.user_id || item.email;
        return itemUserId && allowedIds.includes(itemUserId);
      });
    },

    hasMultipleUsers(minUsers = 2) {
      if (!data || items.length === 0) return false;

      const userIds = new Set(
        items.map((item) => item.user_id || item.email).filter(Boolean)
      );

      return userIds.size >= minUsers;
    },

    hasUserData(userName) {
      if (!data) return false;

      const u = user(userName);
      const allowedIds = [u.id, u.username];

      return items.some((item) => {
        const itemUserId = item.user_id || item.email;
        return itemUserId && allowedIds.includes(itemUserId);
      });
    },

    // Order/cart helpers
    userId() {
      return this.field("user_id") || this.field("email");
    },

    total() {
      return parseFloat(this.field("total") || 0);
    },

    balance() {
      return parseFloat(this.field("balance") || 0);
    },

    items() {
      return this.field("items") || [];
    },

    containsItems(...itemIds) {
      const orderItems = this.items();
      if (!orderItems || orderItems.length === 0) return false;

      const itemIdsInOrder = orderItems.map((item) =>
        String(item.item_id || item.itemId || item.id)
      );

      return itemIds.every((id) => itemIdsInOrder.includes(String(id)));
    },

    last() {
      // If there's created_at field, sort by it, otherwise sort by index
      if (items[0].created_at) {
        return items.sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        )[0];
      }
      return items[items.length - 1];
    },

    first() {
      if (items[0].created_at) {
        return items.sort(
          (a, b) => new Date(a.created_at) - new Date(b.created_at)
        )[0];
      }
      return items[0];
    },

    // Array operations
    map(fn) {
      if (!isArray) return [fn(data)];
      return data.map(fn);
    },

    filter(fn) {
      if (!isArray) return fn(data) ? [data] : [];
      return data.filter(fn);
    },

    find(fn) {
      if (!isArray) return fn(data) ? data : undefined;
      return data.find(fn);
    },

    get(id) {
      return this.find((item) => item.id === id);
    },

    every(fn) {
      if (!isArray) return data ? fn(data) : undefined;
      return data.every(fn);
    },

    // Unwrap to raw data
    unwrap() {
      return data;
    },
  };
}

// ============================================================================
// COOKIE HELPER
// ============================================================================

/**
 * Extract cookie from response.
 * Returns fully-formed cookie ready for Cookie: {{cookie}} header.
 *
 * Example:
 *   POST {{base}}/auth/login
 *   ...
 *   > {%
 *     exports.sessionCookie = extractCookie(response);
 *   %}
 *
 *   GET {{base}}/orders
 *   Cookie: {{sessionCookie}}
 */
function extractCookie(response) {
  const headers = response?.headers?.headers || response?.headers || {};
  const raw = headers["set-cookie"] || headers["Set-Cookie"];

  if (!raw) {
    throw new Error("No Set-Cookie header in response");
  }

  // Handle array or string
  return Array.isArray(raw) ? raw[0] : raw;
}

/**
 * Check if response has a Set-Cookie header (non-throwing version).
 * Returns true/false instead of throwing on missing header.
 *
 * Use this to assert that authentication failures don't set cookies:
 *   ?? js hasCookie(response) == false
 *
 * Example:
 *   POST /auth/login
 *   Content-Type: application/json
 *   {"email": "user@example.com", "password": "wrongpassword"}
 *
 *   ?? js $(response).isError() == true
 *   ?? js hasCookie(response) == false
 */
function hasCookie(response) {
  const headers = response?.headers?.headers || response?.headers || {};
  const raw = headers["set-cookie"] || headers["Set-Cookie"];
  return raw != null;
}

// ============================================================================
// PLATFORM ADMIN (makes actual HTTP requests)
// ============================================================================

const platform = {
  /**
   * Reset database state (E2E testing only)
   * Makes actual HTTP request
   *
   * Example:
   *   {{
   *     await platform.reset();
   *   }}
   */
  async reset() {
    const config = getConfig();
    const response = await fetch(
      `${config.baseUrl}/${config.version}/e2e/reset`,
      {
        method: "POST",
        headers: {
          "X-E2E-API-Key": E2E_API_KEY,
        },
      }
    );

    if (response.status >= 400) {
      throw new Error(`platform.reset() failed: ${response.status}`);
    }

    return response;
  },

  /**
   * Set user balance to a specific amount (E2E testing only)
   * Makes actual HTTP request
   *
   * Example:
   *   {{
   *     await platform.seedCredits("plankton", 200);
   *   }}
   */
  async seedCredits(userName, amount) {
    const config = getConfig();

    const response = await fetch(
      `${config.baseUrl}/${config.version}/e2e/balance`,
      {
        method: "POST",
        headers: {
          "X-E2E-API-Key": E2E_API_KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user(userName).username,
          balance: amount,
        }),
      }
    );

    if (response.status >= 400) {
      throw new Error(`platform.seedCredits() failed: ${response.status}`);
    }

    return response;
  },

  /**
   * Reset and seed multiple users in one call (E2E testing only)
   * Makes actual HTTP requests
   *
   * Example:
   *   {{
   *     await platform.seed({
   *       plankton: 200,
   *       squidward: 150,
   *       spongebob: 100
   *     });
   *   }}
   */
  async seed(users = {}) {
    await this.reset();

    for (const [userName, balance] of Object.entries(users)) {
      await this.seedCredits(userName, balance);
    }
  },
};

// ============================================================================
// MAILPIT HELPERS
// ============================================================================

const mailpit = {
  /**
   * Clear all messages from mailpit
   */
  async clear() {
    await fetch(`${MAILPIT_BASE}/messages`, { method: "DELETE" });
  },

  /**
   * Get the last email sent to a specific address.
   * Returns an object with methods to extract different token types.
   *
   * Example:
   *   @token = {{ await mailpit.lastEmail(regEmail).userToken() }}
   *
   * @param {string} toAddress - Email address to search for
   */
  lastEmail(toAddress) {
    const fetchEmailBody = async () => {
      // Search for emails to this address
      const searchResp = await fetch(
        `${MAILPIT_BASE}/search?query=to:${encodeURIComponent(toAddress)}&limit=1`
      );
      if (!searchResp.ok) {
        throw new Error(`mailpit.lastEmail("${toAddress}") search failed: ${searchResp.status}`);
      }
      const searchData = await searchResp.json();
      if (!searchData.messages?.length) {
        throw new Error(`No email found for ${toAddress}`);
      }

      // Fetch full message to get body
      const msgResp = await fetch(`${MAILPIT_BASE}/message/${searchData.messages[0].ID}`);
      if (!msgResp.ok) {
        throw new Error(`mailpit.lastEmail("${toAddress}") message fetch failed: ${msgResp.status}`);
      }
      return msgResp.json();
    };

    return {
      /**
       * Extract user registration token from email body.
       * Looks for pattern: token=<alphanumeric>
       */
      async userToken() {
        const msg = await fetchEmailBody();
        const match = msg.Text.match(/token=([A-Za-z0-9._-]+)/);
        if (!match) {
          throw new Error(`No user token found in email to ${toAddress}`);
        }
        return match[1];
      },

      /**
       * Extract restaurant verification token from email body.
       * To be implemented when restaurant verification feature is added.
       */
      async restaurantToken() {
        throw new Error("restaurantToken() not yet implemented");
      },
    };
  },
};

// ============================================================================
// VERIFY (for dynamically created users, e.g., registration tests)
// ============================================================================

const verify = {
  /**
   * Check if credentials can successfully login.
   * For dynamically created accounts (e.g., registration tests).
   * Use user("plankton").canLogin() for predefined users instead.
   *
   * Example:
   *   ?? js await verify.canLogin(regEmail, "password123") == true
   *   ?? js await verify.canLogin(regEmail, "hijacked") == false
   */
  async canLogin(email, password) {
    try {
      const config = getConfig();
      const resp = await fetch(
        `${config.baseUrl}/${config.version}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        }
      );
      return resp.ok;
    } catch {
      return false;
    }
  },

  /**
   * Check if credentials can access account info.
   * For dynamically created accounts (e.g., registration tests).
   *
   * Example:
   *   ?? js await verify.canAccessAccount(regEmail, "password123") == true
   */
  async canAccessAccount(email, password) {
    try {
      const config = getConfig();
      const basic = `Basic ${Buffer.from(`${email}:${password}`).toString("base64")}`;
      const resp = await fetch(
        `${config.baseUrl}/${config.version}/account/info`,
        {
          headers: { Authorization: basic },
        }
      );
      return resp.ok;
    } catch {
      return false;
    }
  },
};

// ============================================================================
// ORDER CALCULATIONS
// ============================================================================

const order = {
  /**
   * Calculate expected order total from item IDs and optional tip
   * @param {Array|string|number} itemIds - Item ID(s) to include
   * @param {number} tip - Optional tip amount (default 0)
   * @returns {number} Expected total
   *
   * Example:
   *   ?? js $(response).total() == {{order.total([4, 5], 2)}}
   */
  total(itemIds, tip = 0) {
    const items = Array.isArray(itemIds) ? itemIds : [itemIds];
    const itemsTotal = items.reduce((sum, id) => {
      const item = menu.item(id);
      return sum + parseFloat(item.price);
    }, 0.0);
    return parseFloat((itemsTotal + tip).toFixed(2));
  },

  /**
   * Calculate expected balance after order
   * @param {number} startBalance - Starting balance
   * @param {Array|string|number} itemIds - Item ID(s) ordered
   * @param {number} tip - Optional tip amount
   * @returns {number} Expected remaining balance
   *
   * Example:
   *   ?? js $(response).field("balance") == {{order.balanceAfter(200, [4, 5], 2)}}
   */
  balanceAfter(startBalance, itemIds, tip = 0) {
    return parseFloat((startBalance - this.total(itemIds, tip)).toFixed(2));
  },
};

// ============================================================================
// UTILITIES
// ============================================================================

function testEmail(prefix = "test") {
  const timestamp = Date.now();
  const random = crypto.randomBytes(3).toString("hex");
  return `${prefix}+${timestamp}_${random}@example.test`;
}

function extractToken(body) {
  const match = body.match(/token[=:]\s*([a-zA-Z0-9_-]+)/);
  return match ? match[1] : "";
}

function uuid() {
  return crypto.randomUUID();
}

function version() {
  return getConfig().version;
}

function versionAtLeast(target) {
  const current = getConfig().versionNum;
  const targetNum = parseInt(target.substring(1));
  return current >= targetNum;
}

function url(endpoint) {
  const config = getConfig();
  const base = `${config.baseUrl}/${config.version}`;
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return base + path;
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = function createUtils(versionOverride) {
  if (versionOverride) {
    process.env.VERSION = versionOverride;
  }

  return {
    // Core
    $,
    auth,
    user,
    menu,
    order,
    platform,
    mailpit,
    verify,

    // Cookie helpers
    extractCookie,
    hasCookie,

    // Utilities
    testEmail,
    extractToken,
    uuid,
    version,
    versionAtLeast,
    url,
  };
};
