from chat import CodeChat
import os
import sys
from typing import List, Dict

def test_file_processing():
    """Test if the system can process different file types."""
    chat = CodeChat()
    chat.ingester.process_directory("test_files")
    
    # Check if files were processed
    file_paths = [meta["file_path"] for meta in chat.ingester.metadata]
    print("\nProcessed files:", file_paths)
    
    # Check if we have embeddings
    print(f"Number of chunks processed: {len(chat.ingester.metadata)}")
    print(f"Number of embeddings in index: {chat.ingester.index.ntotal}")

def test_search_functionality():
    """Test the search functionality with different queries."""
    try:
        chat = CodeChat()
        print("\nInitializing chat and processing files...")
        chat.ingester.process_directory("test_files")
        
        test_queries = [
            "How is the factorial function implemented?",
            "What does the user management system do?",
            "How are theme variables generated?",
        ]
        
        print("\nTesting search functionality:")
        for query in test_queries:
            print(f"\nQuery: {query}")
            results = chat.search_similar(query)
            if not results:
                print("❌ No results found")
                continue
                
            for i, result in enumerate(results, 1):
                print(f"\nResult {i}:")
                print(f"File: {result['file_path']}")
                print(f"Relevance score: {1 / (1 + result['distance']):.2f}")
                print("Content preview:", result['content'][:150].replace('\n', ' '), "...")
        
        return True
    except Exception as e:
        print(f"\n❌ Error in search functionality test: {str(e)}")
        return False

def main():
    print("🚀 Starting tests...")
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OpenAI API key not found in environment variables")
        print("Please ensure your API key is set in the .env file")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("File Processing", test_file_processing),
        ("Search Functionality", test_search_functionality)
    ]
    
    success = True
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test:")
        if not test_func():
            success = False
            print(f"❌ {test_name} test failed")
        else:
            print(f"✅ {test_name} test completed successfully")
    
    # Final summary
    print("\n📊 Test Summary:")
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Please check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 