export type Role = 'admin' | 'analista' | 'supervisor';

export interface LoginResponse {
  access: string;
  refresh: string;
  role: Role;
  email: string;
  full_name: string | null;
}

export interface MeResponse {
  email: string;
  role: Role;
  full_name: string | null;
  username: string;
}

export class AuthApiException extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'AuthApiException';
  }
}
