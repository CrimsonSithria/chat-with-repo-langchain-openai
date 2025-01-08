interface Theme {
    primary: string;
    secondary: string;
    text: {
        primary: string;
        secondary: string;
    };
    spacing: {
        small: number;
        medium: number;
        large: number;
    };
}

/**
 * Default light theme configuration
 */
export const lightTheme: Theme = {
    primary: '#007AFF',
    secondary: '#5856D6',
    text: {
        primary: '#000000',
        secondary: '#666666'
    },
    spacing: {
        small: 8,
        medium: 16,
        large: 24
    }
};

/**
 * Default dark theme configuration
 */
export const darkTheme: Theme = {
    primary: '#0A84FF',
    secondary: '#5E5CE6',
    text: {
        primary: '#FFFFFF',
        secondary: '#AEAEB2'
    },
    spacing: {
        small: 8,
        medium: 16,
        large: 24
    }
};

/**
 * Generate CSS variables from theme
 * @param theme - The theme configuration
 * @returns CSS variable definitions
 */
export function generateThemeVariables(theme: Theme): string {
    return `
        :root {
            --color-primary: ${theme.primary};
            --color-secondary: ${theme.secondary};
            --text-primary: ${theme.text.primary};
            --text-secondary: ${theme.text.secondary};
            --spacing-small: ${theme.spacing.small}px;
            --spacing-medium: ${theme.spacing.medium}px;
            --spacing-large: ${theme.spacing.large}px;
        }
    `;
} 