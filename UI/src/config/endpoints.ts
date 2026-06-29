import type { EndpointModule } from '../types/endpoint';

export const endpointModules: EndpointModule[] = [
  // ─── Auth ──────────────────────────────────────────────
  {
    id: 'auth',
    name: 'Authentication',
    icon: '🔐',
    description: 'User registration, login, and token management',
    endpoints: [
      {
        id: 'auth-register',
        method: 'POST',
        path: '/auth/register',
        description: 'Register a new user',
        requiresAuth: false,
        sampleBody: {
          username: 'john_doe',
          email: 'john@example.com',
          password: 'securePassword123',
          roles: ['Viewer'],
        },
      },
      {
        id: 'auth-login',
        method: 'POST',
        path: '/auth/login',
        description: 'Login and get JWT token',
        requiresAuth: false,
        sampleBody: {
          username: 'john_doe',
          password: 'securePassword123',
        },
      },
      {
        id: 'auth-me',
        method: 'GET',
        path: '/auth/me',
        description: 'Get current user profile',
        requiresAuth: true,
      },
    ],
  },

  // ─── Stores ────────────────────────────────────────────
  {
    id: 'stores',
    name: 'Stores',
    icon: '🏪',
    description: 'Dark store management',
    endpoints: [
      {
        id: 'stores-create',
        method: 'POST',
        path: '/stores',
        description: 'Create a new store',
        requiresAuth: true,
        sampleBody: {
          name: 'Accesco Indiranagar',
          address: '100 Feet Road',
          city: 'Bangalore',
          state: 'Karnataka',
          active: true,
          latitude: 12.9716,
          longitude: 77.6412,
        },
      },
      {
        id: 'stores-list',
        method: 'GET',
        path: '/stores',
        description: 'Get all stores',
        requiresAuth: true,
        queryParams: [
          { name: 'skip', type: 'number', required: false, defaultValue: '0' },
          { name: 'limit', type: 'number', required: false, defaultValue: '100' },
        ],
      },
      {
        id: 'stores-get',
        method: 'GET',
        path: '/stores/:store_id',
        description: 'Get store by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'store_id', type: 'number', required: true, description: 'Store ID' },
        ],
      },
      {
        id: 'stores-update',
        method: 'PUT',
        path: '/stores/:store_id',
        description: 'Update a store',
        requiresAuth: true,
        pathParams: [
          { name: 'store_id', type: 'number', required: true, description: 'Store ID' },
        ],
        sampleBody: {
          name: 'Accesco Koramangala',
          address: '80 Feet Road',
          city: 'Bangalore',
          state: 'Karnataka',
          active: true,
          latitude: 12.9352,
          longitude: 77.6245,
        },
      },
    ],
  },

  // ─── Products ──────────────────────────────────────────
  {
    id: 'products',
    name: 'Products',
    icon: '📦',
    description: 'Product catalog management',
    endpoints: [
      {
        id: 'products-create',
        method: 'POST',
        path: '/products',
        description: 'Create a new product',
        requiresAuth: true,
        sampleBody: {
          sku: 'SKU-001',
          name: 'Organic Milk 1L',
          description: 'Fresh organic whole milk',
          category: 'Dairy',
          unit: 'litre',
          active: true,
        },
      },
      {
        id: 'products-list',
        method: 'GET',
        path: '/products',
        description: 'Get all products',
        requiresAuth: true,
        queryParams: [
          { name: 'skip', type: 'number', required: false, defaultValue: '0' },
          { name: 'limit', type: 'number', required: false, defaultValue: '100' },
        ],
      },
      {
        id: 'products-get',
        method: 'GET',
        path: '/products/:product_id',
        description: 'Get product by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'product_id', type: 'number', required: true, description: 'Product ID' },
        ],
      },
      {
        id: 'products-update',
        method: 'PUT',
        path: '/products/:product_id',
        description: 'Update a product',
        requiresAuth: true,
        pathParams: [
          { name: 'product_id', type: 'number', required: true, description: 'Product ID' },
        ],
        sampleBody: {
          sku: 'SKU-001',
          name: 'Organic Milk 1L',
          description: 'Updated description',
          category: 'Dairy',
          unit: 'litre',
          active: true,
        },
      },
    ],
  },

  // ─── Inventory ─────────────────────────────────────────
  {
    id: 'inventory',
    name: 'Inventory',
    icon: '📊',
    description: 'Stock management and reservations',
    endpoints: [
      {
        id: 'inventory-list',
        method: 'GET',
        path: '/inventory',
        description: 'Get all inventory items',
        requiresAuth: true,
        queryParams: [
          { name: 'skip', type: 'number', required: false, defaultValue: '0' },
          { name: 'limit', type: 'number', required: false, defaultValue: '100' },
        ],
      },
      {
        id: 'inventory-by-store',
        method: 'GET',
        path: '/inventory/store/:store_id',
        description: 'Get inventory by store',
        requiresAuth: true,
        pathParams: [
          { name: 'store_id', type: 'number', required: true, description: 'Store ID' },
        ],
      },
      {
        id: 'inventory-add-stock',
        method: 'POST',
        path: '/inventory/add-stock',
        description: 'Add stock to inventory',
        requiresAuth: true,
        queryParams: [
          { name: 'store_id', type: 'number', required: true, description: 'Store ID' },
          { name: 'product_id', type: 'number', required: true, description: 'Product ID' },
          { name: 'quantity', type: 'number', required: true, description: 'Quantity to add' },
          { name: 'reorder_level', type: 'number', required: false, defaultValue: '10' },
        ],
      },
      {
        id: 'inventory-reserve',
        method: 'POST',
        path: '/inventory/reserve',
        description: 'Reserve inventory stock',
        requiresAuth: true,
        sampleBody: {
          store_id: 1,
          product_id: 1,
          quantity: 5,
          order_id: null,
          expires_in_seconds: 300,
        },
      },
      {
        id: 'inventory-release',
        method: 'POST',
        path: '/inventory/release/:reservation_id',
        description: 'Release a reservation',
        requiresAuth: true,
        pathParams: [
          { name: 'reservation_id', type: 'number', required: true, description: 'Reservation ID' },
        ],
      },
    ],
  },

  // ─── Cart ──────────────────────────────────────────────
  {
    id: 'cart',
    name: 'Cart',
    icon: '🛒',
    description: 'Shopping cart management (Redis-backed)',
    endpoints: [
      {
        id: 'cart-get',
        method: 'GET',
        path: '/cart',
        description: 'Get current user cart',
        requiresAuth: true,
      },
      {
        id: 'cart-add-item',
        method: 'POST',
        path: '/cart/items',
        description: 'Add item to cart',
        requiresAuth: true,
        sampleBody: {
          product_id: 1,
          quantity: 2,
        },
      },
      {
        id: 'cart-update-item',
        method: 'PUT',
        path: '/cart/items',
        description: 'Update cart item quantity',
        requiresAuth: true,
        sampleBody: {
          product_id: 1,
          quantity: 5,
        },
      },
      {
        id: 'cart-remove-item',
        method: 'DELETE',
        path: '/cart/items/:product_id',
        description: 'Remove item from cart',
        requiresAuth: true,
        pathParams: [
          { name: 'product_id', type: 'number', required: true, description: 'Product ID' },
        ],
      },
      {
        id: 'cart-clear',
        method: 'DELETE',
        path: '/cart',
        description: 'Clear entire cart',
        requiresAuth: true,
      },
    ],
  },

  // ─── Orders ────────────────────────────────────────────
  {
    id: 'orders',
    name: 'Orders',
    icon: '🧾',
    description: 'Order placement and management',
    endpoints: [
      {
        id: 'orders-create',
        method: 'POST',
        path: '/orders',
        description: 'Place a new order',
        requiresAuth: true,
        sampleBody: {
          items: [
            { product_id: 1, quantity: 2, price: 49.99 },
            { product_id: 2, quantity: 1, price: 29.99 },
          ],
          store_id: 1,
          latitude: 12.9716,
          longitude: 77.6412,
        },
      },
      {
        id: 'orders-get',
        method: 'GET',
        path: '/orders/:order_id',
        description: 'Get order by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'order_id', type: 'number', required: true, description: 'Order ID' },
        ],
      },
      {
        id: 'orders-cancel',
        method: 'POST',
        path: '/orders/:order_id/cancel',
        description: 'Cancel an order',
        requiresAuth: true,
        pathParams: [
          { name: 'order_id', type: 'number', required: true, description: 'Order ID' },
        ],
      },
    ],
  },

  // ─── Payments ──────────────────────────────────────────
  {
    id: 'payments',
    name: 'Payments',
    icon: '💳',
    description: 'Razorpay checkout and webhooks',
    endpoints: [
      {
        id: 'payments-checkout',
        method: 'POST',
        path: '/payments/checkout',
        description: 'Create Razorpay checkout session',
        requiresAuth: true,
        sampleBody: {
          order_id: 1,
        },
      },
      {
        id: 'payments-webhook',
        method: 'POST',
        path: '/webhooks/razorpay',
        description: 'Razorpay webhook handler',
        requiresAuth: false,
        sampleBody: {
          event: 'payment.captured',
          payload: {
            payment: {
              entity: {
                id: 'pay_test123',
                order_id: 'order_test123',
                amount: 5000,
                currency: 'INR',
                status: 'captured',
              },
            },
          },
        },
      },
    ],
  },

  // ─── Procurement ───────────────────────────────────────
  {
    id: 'procurement',
    name: 'Procurement',
    icon: '📋',
    description: 'Purchase order management',
    endpoints: [
      {
        id: 'procurement-create-po',
        method: 'POST',
        path: '/procurement/purchase-orders',
        description: 'Create purchase order',
        requiresAuth: true,
        sampleBody: {
          supplier_name: 'Dairy Fresh Pvt Ltd',
          status: 'DRAFT',
          items: [
            { product_id: 1, quantity: 100 },
            { product_id: 2, quantity: 50 },
          ],
        },
      },
      {
        id: 'procurement-list-pos',
        method: 'GET',
        path: '/procurement/purchase-orders',
        description: 'Get all purchase orders',
        requiresAuth: true,
        queryParams: [
          { name: 'skip', type: 'number', required: false, defaultValue: '0' },
          { name: 'limit', type: 'number', required: false, defaultValue: '100' },
        ],
      },
      {
        id: 'procurement-get-po',
        method: 'GET',
        path: '/procurement/purchase-orders/:po_id',
        description: 'Get purchase order by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'po_id', type: 'number', required: true, description: 'Purchase Order ID' },
        ],
      },
      {
        id: 'procurement-receive-po',
        method: 'POST',
        path: '/procurement/purchase-orders/:po_id/receive',
        description: 'Receive purchase order into store',
        requiresAuth: true,
        pathParams: [
          { name: 'po_id', type: 'number', required: true, description: 'Purchase Order ID' },
        ],
        queryParams: [
          { name: 'store_id', type: 'number', required: true, description: 'Target Store ID' },
        ],
      },
    ],
  },

  // ─── Riders ────────────────────────────────────────────
  {
    id: 'riders',
    name: 'Riders',
    icon: '🏍️',
    description: 'Delivery rider management',
    endpoints: [
      {
        id: 'riders-create',
        method: 'POST',
        path: '/riders',
        description: 'Register a new rider',
        requiresAuth: true,
        sampleBody: {
          name: 'Rajesh Kumar',
          phone: '+919876543210',
          latitude: 12.9716,
          longitude: 77.6412,
          is_available: true,
          status: 'IDLE',
        },
      },
      {
        id: 'riders-list',
        method: 'GET',
        path: '/riders',
        description: 'Get all riders',
        requiresAuth: true,
      },
      {
        id: 'riders-get',
        method: 'GET',
        path: '/riders/:rider_id',
        description: 'Get rider by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'rider_id', type: 'number', required: true, description: 'Rider ID' },
        ],
      },
      {
        id: 'riders-update',
        method: 'PUT',
        path: '/riders/:rider_id',
        description: 'Update rider details',
        requiresAuth: true,
        pathParams: [
          { name: 'rider_id', type: 'number', required: true, description: 'Rider ID' },
        ],
        sampleBody: {
          name: 'Rajesh Kumar',
          phone: '+919876543210',
          latitude: 12.9716,
          longitude: 77.6412,
          is_available: true,
          status: 'IDLE',
        },
      },
      {
        id: 'riders-delete',
        method: 'DELETE',
        path: '/riders/:rider_id',
        description: 'Delete a rider',
        requiresAuth: true,
        pathParams: [
          { name: 'rider_id', type: 'number', required: true, description: 'Rider ID' },
        ],
      },
    ],
  },

  // ─── Dispatch ──────────────────────────────────────────
  {
    id: 'dispatch',
    name: 'Dispatch',
    icon: '🚀',
    description: 'Order dispatch engine, rider assignment, and batching',
    endpoints: [
      {
        id: 'dispatch-assign',
        method: 'POST',
        path: '/dispatch/assign/:order_id',
        description: 'Assign order to rider',
        requiresAuth: false,
        pathParams: [
          { name: 'order_id', type: 'number', required: true, description: 'Order ID' },
        ],
      },
      {
        id: 'dispatch-rider-respond',
        method: 'POST',
        path: '/dispatch/rider/respond',
        description: 'Rider accept/reject assignment',
        requiresAuth: false,
        sampleBody: {
          rider_id: 1,
          order_id: 1,
          batch_id: null,
          accepted: true,
        },
      },
      {
        id: 'dispatch-rider-heartbeat',
        method: 'POST',
        path: '/dispatch/rider/heartbeat',
        description: 'Record rider heartbeat / location',
        requiresAuth: false,
        sampleBody: {
          rider_id: 1,
          latitude: 12.9716,
          longitude: 77.6412,
          battery_level: 85.0,
        },
      },
      {
        id: 'dispatch-rider-transition',
        method: 'POST',
        path: '/dispatch/rider/transition',
        description: 'Force rider state transition',
        requiresAuth: false,
        sampleBody: {
          rider_id: 1,
          target_state: 'EN_ROUTE_PICKUP',
        },
      },
      {
        id: 'dispatch-batches',
        method: 'GET',
        path: '/dispatch/batches',
        description: 'List active dispatch batches',
        requiresAuth: false,
      },
      {
        id: 'dispatch-batch-detail',
        method: 'GET',
        path: '/dispatch/batches/:batch_id',
        description: 'Get batch details',
        requiresAuth: false,
        pathParams: [
          { name: 'batch_id', type: 'number', required: true, description: 'Batch ID' },
        ],
      },
      {
        id: 'dispatch-sweep',
        method: 'POST',
        path: '/dispatch/sweep',
        description: 'Trigger manual sweep cycle',
        requiresAuth: false,
      },
    ],
  },

  // ─── Communities ───────────────────────────────────────
  {
    id: 'communities',
    name: 'Communities',
    icon: '🏘️',
    description: 'Delivery community zone management',
    endpoints: [
      {
        id: 'communities-create',
        method: 'POST',
        path: '/communities',
        description: 'Create a community zone',
        requiresAuth: true,
        sampleBody: {
          id: 'prestige-lakeside',
          name: 'Prestige Lakeside Habitat',
          centroid_latitude: 12.8986,
          centroid_longitude: 77.6458,
          polygon: {
            type: 'Polygon',
            coordinates: [
              [
                [77.644, 12.897],
                [77.648, 12.897],
                [77.648, 12.900],
                [77.644, 12.900],
                [77.644, 12.897],
              ],
            ],
          },
          entry_points: [
            { name: 'Main Gate', latitude: 12.8990, longitude: 77.6450 },
          ],
          avg_walk_time_min: 3.0,
          batch_window_sec: 120,
          max_batch_size: 4,
        },
      },
      {
        id: 'communities-list',
        method: 'GET',
        path: '/communities',
        description: 'Get all communities',
        requiresAuth: true,
      },
      {
        id: 'communities-get',
        method: 'GET',
        path: '/communities/:community_id',
        description: 'Get community by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'community_id', type: 'string', required: true, description: 'Community ID (slug)' },
        ],
      },
      {
        id: 'communities-update',
        method: 'PUT',
        path: '/communities/:community_id',
        description: 'Update a community',
        requiresAuth: true,
        pathParams: [
          { name: 'community_id', type: 'string', required: true, description: 'Community ID (slug)' },
        ],
        sampleBody: {
          name: 'Updated Community Name',
          avg_walk_time_min: 4.0,
          batch_window_sec: 180,
          max_batch_size: 6,
        },
      },
      {
        id: 'communities-delete',
        method: 'DELETE',
        path: '/communities/:community_id',
        description: 'Delete a community',
        requiresAuth: true,
        pathParams: [
          { name: 'community_id', type: 'string', required: true, description: 'Community ID (slug)' },
        ],
      },
    ],
  },

  // ─── Audit Logs ────────────────────────────────────────
  {
    id: 'audit-logs',
    name: 'Audit Logs',
    icon: '📜',
    description: 'System audit trail (Admin only)',
    endpoints: [
      {
        id: 'audit-logs-list',
        method: 'GET',
        path: '/audit-logs',
        description: 'Get all audit logs',
        requiresAuth: true,
        queryParams: [
          { name: 'skip', type: 'number', required: false, defaultValue: '0' },
          { name: 'limit', type: 'number', required: false, defaultValue: '100' },
          { name: 'user_id', type: 'number', required: false, description: 'Filter by user ID' },
          { name: 'module', type: 'string', required: false, description: 'Filter by module name' },
          { name: 'action', type: 'string', required: false, description: 'Filter by action type' },
          { name: 'entity_id', type: 'string', required: false, description: 'Filter by entity ID' },
          { name: 'start_date', type: 'string', required: false, description: 'ISO datetime start filter' },
          { name: 'end_date', type: 'string', required: false, description: 'ISO datetime end filter' },
        ],
      },
      {
        id: 'audit-logs-get',
        method: 'GET',
        path: '/audit-logs/:log_id',
        description: 'Get audit log by ID',
        requiresAuth: true,
        pathParams: [
          { name: 'log_id', type: 'number', required: true, description: 'Audit Log ID' },
        ],
      },
    ],
  },
];
