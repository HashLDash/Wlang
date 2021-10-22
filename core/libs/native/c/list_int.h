#include <stdio.h>
#include <stdlib.h>

typedef struct list_int {
    int len;  // number of element stored
    int size; // allocated array size
    int* values;
} list_int;

int list_int_get(list_int* list, int index) {
    if (index < 0) {
        // -1 is equivalent to the last element
        index = list->len + index;
    }
    if (index < 0 || index > list->len) {
        printf("IndexError: The array has %d elements, but you required the %d index\n", list->len, index);
        exit(-1);
    }
    return list->values[index];
}

void list_int_set(list_int* list, int index, int value) {
    if (index < 0) {
        // -1 is equivalent to the last element
        index = list->len + index;
    }
    if (index < 0 || index > list->len) {
        printf("IndexError: The array has %d elements, but you required the %d index\n", list->len, index);
        exit(-1);
    }
    list->values[index] = value;
}

void list_int_append(list_int* list, int value) {
    if (list->len >= list->size) {
        list->size = list->size * 2;
        list->values = realloc(list->values, sizeof(int) * list->size);
    }
    list->values[list->len] = value;
    list->len += 1;
}

void list_int_removeAll(list_int* list, int value) {
    int removedItems = 0;
    int listLen = list->len;
    for (int i=0; i<listLen-removedItems; i++) {
        if (list->values[i] == value) {
            removedItems++;
        }
        list->values[i] = list->values[i+removedItems];
    }
    list->len -= removedItems;
    if (list->size >= 4*list->len) {
        list->size = list->size / 2;
        list->values = realloc(list->values, sizeof(int) * list->size);
    }
}

void list_int_del(list_int* list, int index) {
    int listLen = list->len;
    for (int i=index; i<listLen-1; i++) {
        list->values[i] = list->values[i+1];
    }
    list->len -= 1;
    if (list->size >= 4*list->len) {
        list->size = list->size / 2;
        list->values = realloc(list->values, sizeof(int) * list->size);
    }
}

void list_int_inc(list_int* list, int index, int value) {
    if (index < 0) {
        // -1 is equivalent to the last element
        index = list->len + index;
    }
    if (index < 0 || index > list->len) {
        printf("IndexError: The array has %d elements, but you required the %d index\n", list->len, index);
        exit(-1);
    }
    list->values[index] += value;
}
