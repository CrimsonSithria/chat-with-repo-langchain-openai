// User management class
class UserManager {
    constructor() {
        this.users = new Map();
    }

    /**
     * Add a new user to the system
     * @param {string} username - The username
     * @param {Object} userData - User information
     * @throws {Error} If user already exists
     */
    addUser(username, userData) {
        if (this.users.has(username)) {
            throw new Error('User already exists');
        }
        this.users.set(username, {
            ...userData,
            createdAt: new Date(),
            lastLogin: null
        });
    }

    /**
     * Get user information
     * @param {string} username - The username to look up
     * @returns {Object|null} User data or null if not found
     */
    getUser(username) {
        return this.users.get(username) || null;
    }

    /**
     * Update user's last login time
     * @param {string} username - The username to update
     * @returns {boolean} True if successful, false if user not found
     */
    updateLastLogin(username) {
        if (!this.users.has(username)) {
            return false;
        }
        const userData = this.users.get(username);
        userData.lastLogin = new Date();
        this.users.set(username, userData);
        return true;
    }
}

// Authentication service
const AuthService = {
    /**
     * Validate user credentials
     * @param {string} username - The username
     * @param {string} password - The password
     * @returns {Promise<boolean>} True if credentials are valid
     */
    async validateCredentials(username, password) {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 100));
        return password.length >= 8;
    },

    /**
     * Generate authentication token
     * @param {string} username - The username
     * @returns {string} JWT token
     */
    generateToken(username) {
        return `token_${username}_${Date.now()}`;
    }
}; 