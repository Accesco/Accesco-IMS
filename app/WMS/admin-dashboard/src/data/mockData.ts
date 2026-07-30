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