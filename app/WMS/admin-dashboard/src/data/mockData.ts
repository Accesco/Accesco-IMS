export const kpiCards = [
  { title: "Receiving Accuracy", value: "98.7%", change: "+1.2%", tone: "green" },
  { title: "Put-away Time", value: "24 min", change: "-8.5%", tone: "blue" },
  { title: "Location Accuracy", value: "99.1%", change: "+0.4%", tone: "green" },
  { title: "Pick Time / Order", value: "82 sec", change: "-6.1%", tone: "purple" },
  { title: "Active Pick Waves", value: 12, change: "+3", tone: "blue" },
  { title: "Pending Pick Tasks", value: 46, change: "+9", tone: "orange" },
  { title: "Dispatch On-Time", value: "96.8%", change: "-1.3%", tone: "teal" },
  { title: "Shrinkage Rate", value: "0.7%", change: "-0.2%", tone: "red" },
] as const;


export const pickingQueue = [
  {
    waveId: "PW-1042",
    picker: "Ravi Kumar",
    zone: "Fast Moving FMCG",
    status: "In Progress",
    pendingItems: 18,
    sla: "07 min",
  },
  {
    waveId: "PW-1043",
    picker: "Aisha Khan",
    zone: "Cold Chain",
    status: "Pending",
    pendingItems: 24,
    sla: "12 min",
  },
  {
    waveId: "PW-1044",
    picker: "Manoj S",
    zone: "High Value",
    status: "Delayed",
    pendingItems: 9,
    sla: "Overdue",
  },
  {
    waveId: "PW-1045",
    picker: "Priya Nair",
    zone: "Staples",
    status: "Packing",
    pendingItems: 6,
    sla: "03 min",
  },
] as const;


export const inventoryAlerts = [
  {
    type: "Low Stock",
    item: "Organic Milk 1L",
    location: "Cold Chain / Bin C-12",
    severity: "High",
  },
  {
    type: "Expiry Risk",
    item: "Paneer 200g",
    location: "Cold Chain / Bin C-08",
    severity: "Medium",
  },
  {
    type: "Misplaced Stock",
    item: "Rice 5kg",
    location: "Staples / Bin S-04",
    severity: "Medium",
  },
  {
    type: "Quarantine",
    item: "Protein Bar Pack",
    location: "QC Hold Area",
    severity: "High",
  },
] as const;

export const systemHealth = [
  { service: "WMS Core", uptime: "99.94%", status: "Operational" },
  { service: "Inventory Sync", uptime: "99.91%", status: "Operational" },
  { service: "Scanner Service", uptime: "99.78%", status: "Operational" },
  { service: "Dispatch Integration", uptime: "98.62%", status: "Degraded" },
] as const;



export const dispatchQueue = [
  {
    orderId: "ORD-84801",
    zone: "Zone A",
    packedStatus: "Packed",
    handoffStatus: "Ready",
    carrier: "Internal Rider",
  },
  {
    orderId: "ORD-84802",
    zone: "Zone B",
    packedStatus: "Packing",
    handoffStatus: "Waiting",
    carrier: "Internal Rider",
  },
  {
    orderId: "ORD-84803",
    zone: "Cold Chain",
    packedStatus: "QC Hold",
    handoffStatus: "Blocked",
    carrier: "Cold Chain Fleet",
  },
  {
    orderId: "ORD-84804",
    zone: "Zone C",
    packedStatus: "Packed",
    handoffStatus: "Assigned",
    carrier: "Internal Rider",
  },
] as const;


export const warehouseStatus = [
  { area: "Receiving", state: "Active", tone: "green" },
  { area: "Picking", state: "Normal", tone: "green" },
  { area: "Packing", state: "Busy", tone: "orange" },
  { area: "Dispatch", state: "Delayed", tone: "red" },
] as const;


export const notifications = [
  {
    title: "SKU running low",
    detail: "Organic Milk 1L is below reorder level in Cold Chain.",
    time: "4 min ago",
    tone: "orange",
  },
  {
    title: "Pick wave delayed",
    detail: "PW-1044 has crossed the SLA target.",
    time: "9 min ago",
    tone: "red",
  },
  {
    title: "Shipment arrived",
    detail: "PO-7712 is ready for receiving at Dock 2.",
    time: "16 min ago",
    tone: "green",
  },
  {
    title: "Cycle count variance",
    detail: "Rice 5kg variance detected in Staples / Bin S-04.",
    time: "22 min ago",
    tone: "blue",
  },
] as const;






export const receivingQueue = [
  {
    poNumber: "PO-7712",
    supplier: "Dairy Fresh Pvt Ltd",
    dock: "Dock 2",
    expectedUnits: 240,
    receivedUnits: 216,
    qcStatus: "In QC",
    status: "Receiving",
  },
  {
    poNumber: "PO-7713",
    supplier: "FarmChain Produce",
    dock: "Dock 1",
    expectedUnits: 180,
    receivedUnits: 180,
    qcStatus: "Passed",
    status: "Completed",
  },
  {
    poNumber: "PO-7714",
    supplier: "MedSupply Local",
    dock: "Dock 3",
    expectedUnits: 90,
    receivedUnits: 72,
    qcStatus: "Hold",
    status: "Variance",
  },
  {
    poNumber: "PO-7715",
    supplier: "Staples Wholesale",
    dock: "Dock 4",
    expectedUnits: 320,
    receivedUnits: 320,
    qcStatus: "Pending",
    status: "Queued",
  },
] as const;




export const putawayTasks = [
  {
    taskId: "PA-2201",
    sku: "Organic Milk 1L",
    category: "Cold Chain",
    suggestedBin: "C-12",
    priority: "High",
    status: "Assigned",
  },
  {
    taskId: "PA-2202",
    sku: "Rice 5kg",
    category: "Staples",
    suggestedBin: "S-04",
    priority: "Medium",
    status: "Pending",
  },
  {
    taskId: "PA-2203",
    sku: "Protein Bar Pack",
    category: "Fast Moving FMCG",
    suggestedBin: "F-02",
    priority: "High",
    status: "In Progress",
  },
  {
    taskId: "PA-2204",
    sku: "Paneer 200g",
    category: "Cold Chain",
    suggestedBin: "C-08",
    priority: "High",
    status: "Blocked",
  },
] as const;


/*Picking and packing */

export const locationInventory = [
  {
    sku: "Organic Milk 1L",
    zone: "Cold Chain",
    bin: "C-12",
    systemQty: 120,
    physicalQty: 118,
    status: "Variance",
  },
  {
    sku: "Rice 5kg",
    zone: "Staples",
    bin: "S-04",
    systemQty: 64,
    physicalQty: 64,
    status: "Matched",
  },
  {
    sku: "Protein Bar Pack",
    zone: "Fast Moving FMCG",
    bin: "F-02",
    systemQty: 210,
    physicalQty: 210,
    status: "Matched",
  },
  {
    sku: "Paneer 200g",
    zone: "Cold Chain",
    bin: "C-08",
    systemQty: 42,
    physicalQty: 36,
    status: "Recount",
  },
] as const;


/*Quality & Compliance Check*/

export const qualityChecks = [
  {
    checkId: "QC-3101",
    item: "Organic Milk 1L",
    issue: "Temperature variance",
    zone: "Cold Chain",
    status: "In Review",
    owner: "Quality Team",
  },
  {
    checkId: "QC-3102",
    item: "Protein Bar Pack",
    issue: "Damaged outer cartons",
    zone: "QC Hold Area",
    status: "Hold",
    owner: "Compliance",
  },
  {
    checkId: "QC-3103",
    item: "Paneer 200g",
    issue: "Expiry risk",
    zone: "Cold Chain",
    status: "Action Needed",
    owner: "Warehouse Lead",
  },
  {
    checkId: "QC-3104",
    item: "Rice 5kg",
    issue: "Cycle count variance",
    zone: "Staples",
    status: "Resolved",
    owner: "Inventory Team",
  },
] as const;


/*Report*/

export const reportsSummary = [
  {
    reportName: "Cycle Count Variance Report",
    category: "Inventory Accuracy",
    frequency: "Daily",
    owner: "Inventory Team",
    status: "Ready",
  },
  {
    reportName: "Picking Performance Report",
    category: "Warehouse Productivity",
    frequency: "Shift-wise",
    owner: "Warehouse Ops",
    status: "Ready",
  },
  {
    reportName: "Dispatch SLA Report",
    category: "Outbound Operations",
    frequency: "Daily",
    owner: "Dispatch Lead",
    status: "Pending",
  },
  {
    reportName: "Quality Hold Report",
    category: "Compliance",
    frequency: "Weekly",
    owner: "Quality Team",
    status: "Ready",
  },
] as const;