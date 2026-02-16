# Some methods in Java can return null, but that info is not available via
# reflections. This info is only documented in the Javadoc. So this is a 
# whitelist of such methods.
METHOD_CAN_RETURN_NONE = {
    # =====================================================================
    # java.lang
    # =====================================================================

    # Class methods
    "java.lang.Class.getAnnotation(java.lang.Class)",
    "java.lang.Class.getDeclaredAnnotation(java.lang.Class)",
    "java.lang.Class.getCanonicalName()",
    "java.lang.Class.getClassLoader()",
    "java.lang.Class.getComponentType()",
    "java.lang.Class.getDeclaringClass()",
    "java.lang.Class.getEnclosingClass()",
    "java.lang.Class.getEnclosingConstructor()",
    "java.lang.Class.getEnclosingMethod()",
    "java.lang.Class.getEnumConstants()",
    "java.lang.Class.getNestHost()",
    "java.lang.Class.getPackage()",
    "java.lang.Class.getResource(java.lang.String)",
    "java.lang.Class.getResourceAsStream(java.lang.String)",
    "java.lang.Class.getSigners()",
    "java.lang.Class.getSuperclass()",
    "java.lang.Class.cast(java.lang.Object)",

    # ClassLoader methods
    "java.lang.ClassLoader.getParent()",
    "java.lang.ClassLoader.getResource(java.lang.String)",
    "java.lang.ClassLoader.getResourceAsStream(java.lang.String)",
    "java.lang.ClassLoader.getSystemClassLoader()",
    "java.lang.ClassLoader.getSystemResource(java.lang.String)",
    "java.lang.ClassLoader.getSystemResourceAsStream(java.lang.String)",

    # Package methods
    "java.lang.Package.getAnnotation(java.lang.Class)",
    "java.lang.Package.getImplementationTitle()",
    "java.lang.Package.getImplementationVendor()",
    "java.lang.Package.getImplementationVersion()",
    "java.lang.Package.getPackage(java.lang.String)",
    "java.lang.Package.getSpecificationTitle()",
    "java.lang.Package.getSpecificationVendor()",
    "java.lang.Package.getSpecificationVersion()",

    # System methods
    "java.lang.System.console()",
    "java.lang.System.getProperty(java.lang.String)",
    "java.lang.System.getSecurityManager()",
    "java.lang.System.getenv(java.lang.String)",

    # Thread methods
    "java.lang.Thread.getContextClassLoader()",
    "java.lang.Thread.getDefaultUncaughtExceptionHandler()",
    "java.lang.Thread.getUncaughtExceptionHandler()",
    "java.lang.ThreadGroup.getParent()",
    "java.lang.ThreadLocal.get()",

    # ProcessBuilder methods
    "java.lang.ProcessBuilder.directory()",

    # =====================================================================
    # java.lang.ref
    # =====================================================================
    "java.lang.ref.Reference.get()",
    "java.lang.ref.SoftReference.get()",
    "java.lang.ref.PhantomReference.get()",
    "java.lang.ref.ReferenceQueue.poll()",

    # =====================================================================
    # java.lang.reflect
    # =====================================================================
    "java.lang.reflect.AnnotatedElement.getAnnotation(java.lang.Class)",
    "java.lang.reflect.AnnotatedElement.getDeclaredAnnotation(java.lang.Class)",
    "java.lang.reflect.AccessibleObject.getAnnotation(java.lang.Class)",
    "java.lang.reflect.AccessibleObject.getDeclaredAnnotation(java.lang.Class)",
    "java.lang.reflect.Executable.getAnnotation(java.lang.Class)",
    "java.lang.reflect.Constructor.getAnnotation(java.lang.Class)",
    "java.lang.reflect.Field.get(java.lang.Object)",
    "java.lang.reflect.Field.getAnnotation(java.lang.Class)",
    "java.lang.reflect.Method.getAnnotation(java.lang.Class)",
    "java.lang.reflect.Method.getDefaultValue()",
    "java.lang.reflect.Method.invoke(java.lang.Object, java.lang.Object[])",
    "java.lang.reflect.Parameter.getAnnotation(java.lang.Class)",
    "java.lang.reflect.Parameter.getDeclaredAnnotation(java.lang.Class)",

    # =====================================================================
    # java.util - Map interface and implementations
    # =====================================================================

    # Map interface
    "java.util.Map.get(java.lang.Object)",
    "java.util.Map.put(java.lang.Object, java.lang.Object)",
    "java.util.Map.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.Map.remove(java.lang.Object)",
    "java.util.Map.replace(java.lang.Object, java.lang.Object)",
    "java.util.Map.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.Map.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.Map.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.Map.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",

    # Dictionary
    "java.util.Dictionary.get(java.lang.Object)",
    "java.util.Dictionary.put(java.lang.Object, java.lang.Object)",
    "java.util.Dictionary.remove(java.lang.Object)",

    # Hashtable
    "java.util.Hashtable.get(java.lang.Object)",
    "java.util.Hashtable.put(java.lang.Object, java.lang.Object)",
    "java.util.Hashtable.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.Hashtable.remove(java.lang.Object)",
    "java.util.Hashtable.replace(java.lang.Object, java.lang.Object)",
    "java.util.Hashtable.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.Hashtable.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.Hashtable.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.Hashtable.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",

    # HashMap
    "java.util.HashMap.get(java.lang.Object)",
    "java.util.HashMap.put(java.lang.Object, java.lang.Object)",
    "java.util.HashMap.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.HashMap.remove(java.lang.Object)",
    "java.util.HashMap.replace(java.lang.Object, java.lang.Object)",
    "java.util.HashMap.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.HashMap.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.HashMap.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.HashMap.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",

    # LinkedHashMap
    "java.util.LinkedHashMap.get(java.lang.Object)",

    # TreeMap
    "java.util.TreeMap.get(java.lang.Object)",
    "java.util.TreeMap.put(java.lang.Object, java.lang.Object)",
    "java.util.TreeMap.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.TreeMap.remove(java.lang.Object)",
    "java.util.TreeMap.replace(java.lang.Object, java.lang.Object)",
    "java.util.TreeMap.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.TreeMap.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.TreeMap.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.TreeMap.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",
    "java.util.TreeMap.lowerEntry(java.lang.Object)",
    "java.util.TreeMap.lowerKey(java.lang.Object)",
    "java.util.TreeMap.floorEntry(java.lang.Object)",
    "java.util.TreeMap.floorKey(java.lang.Object)",
    "java.util.TreeMap.ceilingEntry(java.lang.Object)",
    "java.util.TreeMap.ceilingKey(java.lang.Object)",
    "java.util.TreeMap.higherEntry(java.lang.Object)",
    "java.util.TreeMap.higherKey(java.lang.Object)",
    "java.util.TreeMap.firstEntry()",
    "java.util.TreeMap.lastEntry()",
    "java.util.TreeMap.pollFirstEntry()",
    "java.util.TreeMap.pollLastEntry()",

    # WeakHashMap
    "java.util.WeakHashMap.get(java.lang.Object)",
    "java.util.WeakHashMap.put(java.lang.Object, java.lang.Object)",
    "java.util.WeakHashMap.remove(java.lang.Object)",

    # EnumMap
    "java.util.EnumMap.get(java.lang.Object)",
    "java.util.EnumMap.put(java.lang.Enum, java.lang.Object)",
    "java.util.EnumMap.remove(java.lang.Object)",

    # IdentityHashMap
    "java.util.IdentityHashMap.get(java.lang.Object)",
    "java.util.IdentityHashMap.put(java.lang.Object, java.lang.Object)",
    "java.util.IdentityHashMap.remove(java.lang.Object)",

    # SortedMap interface
    "java.util.SortedMap.firstKey()",
    "java.util.SortedMap.lastKey()",

    # NavigableMap interface
    "java.util.NavigableMap.lowerEntry(java.lang.Object)",
    "java.util.NavigableMap.lowerKey(java.lang.Object)",
    "java.util.NavigableMap.floorEntry(java.lang.Object)",
    "java.util.NavigableMap.floorKey(java.lang.Object)",
    "java.util.NavigableMap.ceilingEntry(java.lang.Object)",
    "java.util.NavigableMap.ceilingKey(java.lang.Object)",
    "java.util.NavigableMap.higherEntry(java.lang.Object)",
    "java.util.NavigableMap.higherKey(java.lang.Object)",
    "java.util.NavigableMap.firstEntry()",
    "java.util.NavigableMap.lastEntry()",
    "java.util.NavigableMap.pollFirstEntry()",
    "java.util.NavigableMap.pollLastEntry()",

    # =====================================================================
    # java.util - Queue, Deque, and implementations
    # =====================================================================

    # Queue interface
    "java.util.Queue.peek()",
    "java.util.Queue.poll()",

    # Deque interface
    "java.util.Deque.peek()",
    "java.util.Deque.poll()",
    "java.util.Deque.peekFirst()",
    "java.util.Deque.peekLast()",
    "java.util.Deque.pollFirst()",
    "java.util.Deque.pollLast()",

    # LinkedList (overrides Queue/Deque methods)
    "java.util.LinkedList.peek()",
    "java.util.LinkedList.poll()",
    "java.util.LinkedList.peekFirst()",
    "java.util.LinkedList.peekLast()",
    "java.util.LinkedList.pollFirst()",
    "java.util.LinkedList.pollLast()",

    # ArrayDeque (overrides Queue/Deque methods)
    "java.util.ArrayDeque.peek()",
    "java.util.ArrayDeque.poll()",
    "java.util.ArrayDeque.peekFirst()",
    "java.util.ArrayDeque.peekLast()",
    "java.util.ArrayDeque.pollFirst()",
    "java.util.ArrayDeque.pollLast()",

    # PriorityQueue
    "java.util.PriorityQueue.peek()",
    "java.util.PriorityQueue.poll()",
    "java.util.PriorityQueue.comparator()",

    # =====================================================================
    # java.util - Set interfaces and implementations
    # =====================================================================

    # SortedSet interface
    "java.util.SortedSet.first()",
    "java.util.SortedSet.last()",
    "java.util.SortedSet.comparator()",

    # NavigableSet interface
    "java.util.NavigableSet.lower(java.lang.Object)",
    "java.util.NavigableSet.higher(java.lang.Object)",
    "java.util.NavigableSet.floor(java.lang.Object)",
    "java.util.NavigableSet.ceiling(java.lang.Object)",
    "java.util.NavigableSet.pollFirst()",
    "java.util.NavigableSet.pollLast()",

    # TreeSet
    "java.util.TreeSet.lower(java.lang.Object)",
    "java.util.TreeSet.higher(java.lang.Object)",
    "java.util.TreeSet.floor(java.lang.Object)",
    "java.util.TreeSet.ceiling(java.lang.Object)",
    "java.util.TreeSet.pollFirst()",
    "java.util.TreeSet.pollLast()",
    "java.util.TreeSet.first()",
    "java.util.TreeSet.last()",

    # =====================================================================
    # java.util - Properties
    # =====================================================================
    "java.util.Properties.getProperty(java.lang.String)",
    "java.util.Properties.getProperty(java.lang.String, java.lang.String)",
    "java.util.Properties.setProperty(java.lang.String, java.lang.String)",

    # =====================================================================
    # java.util.regex
    # =====================================================================
    "java.util.regex.MatchResult.group(int)",
    "java.util.regex.Matcher.group()",
    "java.util.regex.Matcher.group(int)",
    "java.util.regex.Matcher.group(java.lang.String)",

    # =====================================================================
    # java.util.concurrent
    # =====================================================================

    # ConcurrentMap interface
    "java.util.concurrent.ConcurrentMap.get(java.lang.Object)",
    "java.util.concurrent.ConcurrentMap.remove(java.lang.Object)",
    "java.util.concurrent.ConcurrentMap.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentMap.replace(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentMap.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentMap.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.concurrent.ConcurrentMap.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentMap.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",

    # ConcurrentHashMap
    "java.util.concurrent.ConcurrentHashMap.get(java.lang.Object)",
    "java.util.concurrent.ConcurrentHashMap.put(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentHashMap.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentHashMap.remove(java.lang.Object)",
    "java.util.concurrent.ConcurrentHashMap.replace(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentHashMap.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentHashMap.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentHashMap.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.concurrent.ConcurrentHashMap.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",

    # ConcurrentSkipListMap
    "java.util.concurrent.ConcurrentSkipListMap.get(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.put(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.putIfAbsent(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.remove(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.replace(java.lang.Object, java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.merge(java.lang.Object, java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentSkipListMap.compute(java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentSkipListMap.computeIfAbsent(java.lang.Object, java.util.function.Function)",
    "java.util.concurrent.ConcurrentSkipListMap.computeIfPresent(java.lang.Object, java.util.function.BiFunction)",
    "java.util.concurrent.ConcurrentSkipListMap.lowerEntry(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.lowerKey(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.floorEntry(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.floorKey(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.ceilingEntry(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.ceilingKey(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.higherEntry(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.higherKey(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListMap.firstEntry()",
    "java.util.concurrent.ConcurrentSkipListMap.lastEntry()",
    "java.util.concurrent.ConcurrentSkipListMap.pollFirstEntry()",
    "java.util.concurrent.ConcurrentSkipListMap.pollLastEntry()",

    # ConcurrentSkipListSet
    "java.util.concurrent.ConcurrentSkipListSet.lower(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListSet.higher(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListSet.floor(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListSet.ceiling(java.lang.Object)",
    "java.util.concurrent.ConcurrentSkipListSet.pollFirst()",
    "java.util.concurrent.ConcurrentSkipListSet.pollLast()",
    "java.util.concurrent.ConcurrentSkipListSet.first()",
    "java.util.concurrent.ConcurrentSkipListSet.last()",

    # BlockingQueue
    "java.util.concurrent.BlockingQueue.poll(long, java.util.concurrent.TimeUnit)",

    # BlockingDeque
    "java.util.concurrent.BlockingDeque.pollFirst(long, java.util.concurrent.TimeUnit)",
    "java.util.concurrent.BlockingDeque.pollLast(long, java.util.concurrent.TimeUnit)",

    # LinkedBlockingQueue
    "java.util.concurrent.LinkedBlockingQueue.peek()",
    "java.util.concurrent.LinkedBlockingQueue.poll()",
    "java.util.concurrent.LinkedBlockingQueue.poll(long, java.util.concurrent.TimeUnit)",

    # LinkedBlockingDeque
    "java.util.concurrent.LinkedBlockingDeque.peek()",
    "java.util.concurrent.LinkedBlockingDeque.poll()",
    "java.util.concurrent.LinkedBlockingDeque.poll(long, java.util.concurrent.TimeUnit)",
    "java.util.concurrent.LinkedBlockingDeque.peekFirst()",
    "java.util.concurrent.LinkedBlockingDeque.peekLast()",
    "java.util.concurrent.LinkedBlockingDeque.pollFirst()",
    "java.util.concurrent.LinkedBlockingDeque.pollLast()",
    "java.util.concurrent.LinkedBlockingDeque.pollFirst(long, java.util.concurrent.TimeUnit)",
    "java.util.concurrent.LinkedBlockingDeque.pollLast(long, java.util.concurrent.TimeUnit)",

    # ArrayBlockingQueue
    "java.util.concurrent.ArrayBlockingQueue.peek()",
    "java.util.concurrent.ArrayBlockingQueue.poll()",
    "java.util.concurrent.ArrayBlockingQueue.poll(long, java.util.concurrent.TimeUnit)",

    # PriorityBlockingQueue
    "java.util.concurrent.PriorityBlockingQueue.peek()",
    "java.util.concurrent.PriorityBlockingQueue.poll()",
    "java.util.concurrent.PriorityBlockingQueue.poll(long, java.util.concurrent.TimeUnit)",

    # ConcurrentLinkedQueue
    "java.util.concurrent.ConcurrentLinkedQueue.peek()",
    "java.util.concurrent.ConcurrentLinkedQueue.poll()",

    # ConcurrentLinkedDeque
    "java.util.concurrent.ConcurrentLinkedDeque.peek()",
    "java.util.concurrent.ConcurrentLinkedDeque.poll()",
    "java.util.concurrent.ConcurrentLinkedDeque.peekFirst()",
    "java.util.concurrent.ConcurrentLinkedDeque.peekLast()",
    "java.util.concurrent.ConcurrentLinkedDeque.pollFirst()",
    "java.util.concurrent.ConcurrentLinkedDeque.pollLast()",

    # Future / FutureTask
    "java.util.concurrent.Future.get()",
    "java.util.concurrent.Future.get(long, java.util.concurrent.TimeUnit)",
    "java.util.concurrent.FutureTask.get()",
    "java.util.concurrent.FutureTask.get(long, java.util.concurrent.TimeUnit)",

    # =====================================================================
    # java.io
    # =====================================================================
    "java.io.BufferedReader.readLine()",
    "java.io.File.getParent()",
    "java.io.File.getParentFile()",
    "java.io.File.list()",
    "java.io.File.list(java.io.FilenameFilter)",
    "java.io.File.listFiles()",
    "java.io.File.listFiles(java.io.FileFilter)",
    "java.io.File.listFiles(java.io.FilenameFilter)",

    # =====================================================================
    # java.net
    # =====================================================================

    # URI (opaque URIs may return null for many components)
    "java.net.URI.getAuthority()",
    "java.net.URI.getFragment()",
    "java.net.URI.getHost()",
    "java.net.URI.getPath()",
    "java.net.URI.getQuery()",
    "java.net.URI.getRawAuthority()",
    "java.net.URI.getRawFragment()",
    "java.net.URI.getRawPath()",
    "java.net.URI.getRawQuery()",
    "java.net.URI.getRawSchemeSpecificPart()",
    "java.net.URI.getRawUserInfo()",
    "java.net.URI.getScheme()",
    "java.net.URI.getUserInfo()",

    # URL
    "java.net.URL.getAuthority()",
    "java.net.URL.getQuery()",
    "java.net.URL.getRef()",
    "java.net.URL.getUserInfo()",
    "java.net.URL.openConnection()",
    "java.net.URL.openConnection(java.net.Proxy)",
}
