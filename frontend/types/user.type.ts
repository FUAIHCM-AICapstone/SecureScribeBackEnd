// User profile interface (matches backend User model)
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  bio?: string;
  position?: string;
  created_at: string;
  updated_at?: string;
}

// User update request
export interface UserUpdate {
  name?: string;
  bio?: string;
  position?: string;
  avatar_url?: string;
}

// User create request
export interface UserCreate {
  email: string;
  name?: string;
  avatar_url?: string;
  bio?: string;
  position?: string;
}

// Bulk user create request
export interface BulkUserCreate {
  users: UserCreate[];
}

// Bulk user update request
export interface BulkUserUpdateItem {
  id: string;
  updates: UserUpdate;
}

export interface BulkUserUpdate {
  users: BulkUserUpdateItem[];
}