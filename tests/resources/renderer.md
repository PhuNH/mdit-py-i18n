---
authors:
- SPDX-FileCopyrightText: 2023 Phu Hung Nguyen <phuhnguyen@outlook.com>
SPDX-License-Identifier: CC0-1.0
---
# atx heading

setext heading
==

---

paragraph here

and more

    int main() {
        int a = 1;
        return(a)
    }

```c
#include "header.h"
// comment 1
#include "header2.h"
// comment 2
int main() {

// Comment spreaded
// on 2 lines, not indented

    // Comment spreaded
    // on 2 lines, indented



    // A super long long comment
    // on multiple lines
    // trying to make it into 3 lines
    // now the fourth one here
    return 0;

// Last comment
}
```

```python
# function defined by `def` keyword.
# arg is an argument.
# this function does nothing more than showing that addition is possible
def function(arg):
    b = 5
    # c is a variable
    c = arg + b
    
    # return statement
    return c
```

<div>
    <p>html block</p>
    <hr>
</div>

[foo]: /url "title"

this is a reference [foo]. and after the reference.

| head | head2 |
|------|-------|
| body | body2 |

paragraph with  
a hard line break