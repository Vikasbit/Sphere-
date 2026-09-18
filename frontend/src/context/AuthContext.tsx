import React, { useEffect, useState, useCallback } from 'react';
import api from '../lib/api';
import type { User, AuthResponse, SignupResponse } from '../types/auth';
import { AuthContext } from './AuthContextDefinition';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
    try {
      const response = await api.get<User>('/auth/me');
      setUser(response.data);
      return response.data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    api
      .get<User>('/auth/me')
      .then((res) => {
        if (isMounted) setUser(res.data);
      })
      .catch(() => {
        if (isMounted) setUser(null);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string): Promise<User> => {
    const response = await api.post<AuthResponse>('/auth/login', { email, password });
    setUser(response.data.user);
    return response.data.user;
  };

  const signup = async (
    name: string,
    email: string,
    username: string,
    password: string
  ): Promise<SignupResponse> => {
    const response = await api.post<SignupResponse>('/auth/signup', {
      name,
      email,
      username,
      password,
    });
    return response.data;
  };

  const logout = async (): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
        refetchUser: fetchCurrentUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
