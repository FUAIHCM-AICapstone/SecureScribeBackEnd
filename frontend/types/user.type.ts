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