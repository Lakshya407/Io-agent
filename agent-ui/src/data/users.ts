/**
 * Mock data for Users + User Analytics pages.
 * Frontend-only demo — replace with real API responses later.
 */

export interface UserRow {
  id: string;
  name: string;
  email: string;
  status: "Active" | "Inactive";
  conversations: number;
  tokensUsed: string;
  lastActive: string;
  role: "Admin" | "User";
}

export interface DailyActiveUsers {
  day: string;
  users: number;
}

export interface TopUserRow {
  user: string;
  tokens: string;
  conversations: number;
}

export const userStats = {
  total: 128,
  active: 36,
  inactive: 92,
};

export const users: UserRow[] = [
  {
    id: "u1",
    name: "Lakshya",
    email: "lakshya@example.com",
    status: "Active",
    conversations: 24,
    tokensUsed: "320K",
    lastActive: "2 min ago",
    role: "User",
  },
  {
    id: "u2",
    name: "User02",
    email: "user02@example.com",
    status: "Active",
    conversations: 18,
    tokensUsed: "210K",
    lastActive: "10 min ago",
    role: "User",
  },
  {
    id: "u3",
    name: "Admin",
    email: "admin@example.com",
    status: "Active",
    conversations: 42,
    tokensUsed: "580K",
    lastActive: "1 min ago",
    role: "Admin",
  },
  {
    id: "u4",
    name: "Priya Sharma",
    email: "priya@example.com",
    status: "Active",
    conversations: 15,
    tokensUsed: "150K",
    lastActive: "1 hour ago",
    role: "User",
  },
  {
    id: "u5",
    name: "Rahul Verma",
    email: "rahul@example.com",
    status: "Inactive",
    conversations: 7,
    tokensUsed: "90K",
    lastActive: "3 days ago",
    role: "User",
  },
  {
    id: "u6",
    name: "Sneha Patel",
    email: "sneha@example.com",
    status: "Inactive",
    conversations: 3,
    tokensUsed: "45K",
    lastActive: "Last week",
    role: "User",
  },
];

export const analyticsStats = {
  dailyActive: 36,
  monthlyActive: 94,
  totalUsers: 128,
  avgConversationsPerUser: "4.2",
};

export const dailyActiveUsers: DailyActiveUsers[] = [
  { day: "Mon", users: 18 },
  { day: "Tue", users: 24 },
  { day: "Wed", users: 31 },
  { day: "Thu", users: 28 },
  { day: "Fri", users: 36 },
  { day: "Sat", users: 22 },
  { day: "Sun", users: 19 },
];

export const topUsers: TopUserRow[] = [
  { user: "Admin", tokens: "580K", conversations: 42 },
  { user: "Lakshya", tokens: "320K", conversations: 24 },
  { user: "User02", tokens: "210K", conversations: 18 },
  { user: "Priya Sharma", tokens: "150K", conversations: 15 },
  { user: "Rahul Verma", tokens: "90K", conversations: 7 },
];
