import client from '../client';

export const authApi = {
  login: (username: string, password: string): Promise<any> =>
    client.post('/internal/login/', { username, password }),
};
