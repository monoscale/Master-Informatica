#include <string>
#include <iostream>

#include "patriciatrie.h"
int main(void) {
    
    std::string ananas("ananas");
    PatriciaTrie trie;
    trie.voegToe(ananas);
    trie.teken("patriciatrie.dot");

    return 0;
}